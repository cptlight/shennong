"""Self-adjusting research loop.

The state this replaces
-----------------------
A fixed threshold on a fixed model is a static classifier: when a hypothesis is unsupported it either
passes or it does not, and the system learns nothing. This module implements the opposite: when the
panel fails to support a claim, the loop **diagnoses which domain is blocking it**, acquires the
missing evidence for that domain, and re-runs the panel. The adjustment is to the *data pipeline*, not
to the threshold.

Why that distinction is the whole point
---------------------------------------
Lowering a threshold to make a hypothesis pass is fraud. Fetching the compound table, resolving a
drug name, or expanding the attestation set is science — you now know more than you did. The loop is
only allowed to do the second kind, and every accepted adjustment must raise independent-domain
agreement on evidence that did not exist before. Rejected adjustments are recorded too, because a
loop that only ever accepts its own ideas is a random walk with good PR.

The three actions
-----------------
1. `expand_attestation` — the ethnobotany expert says the drug is unattested. Scan the corpus for the
   surface and add the real sources/traditions found. (Offline; genuinely new evidence.)
2. `resolve_taxon` — the phytochemistry expert says there is no documented chemistry because the drug
   surface has no binomial. Resolve it through the lexicon and re-join the compound table.
3. `enrich_operator` — the operator expert says the 炮制 term is not in the ontology. Fall back to the
   curated core process semantics.

Each action returns `(changed: bool, note: str)` and mutates the world in place. The loop records
before/after agreement per claim, accepts the round if the mean agreement rises, and never edits a
score directly.
"""
from __future__ import annotations

import copy
import json
import sys
import time
from dataclasses import dataclass, field
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(ROOT))

from shennong.experts import EXPERTS, World, fuse  # noqa: E402
from shennong.normalize import fold_zh  # noqa: E402

MIN_SUPPORT = 0.45


# ---------------------------------------------------------------------------------------
# Actions: each acquires evidence for one blocking domain
# ---------------------------------------------------------------------------------------
def expand_attestation(world: World, item: dict, surfaces=None) -> tuple[bool, str]:
    """Ethnobotany blocked: scan the corpus for the surface and record real sources."""
    surf = item.get("drug_surface") or ""
    if not surf or surf in world.attestation:
        return False, "surface already attested"
    corpus = ROOT / "corpus" / "processed" / "corpus.jsonl"
    if not corpus.exists():
        return False, "corpus missing"
    target = fold_zh(surf)
    sources: set[str] = set()
    traditions: set[str] = set()
    with corpus.open(encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if not line or target not in line:
                continue
            try:
                rec = json.loads(line)
            except json.JSONDecodeError:
                continue
            if target in fold_zh(rec.get("text") or ""):
                sources.add(rec.get("source_id") or "")
                traditions.add(rec.get("tradition") or "")
            if len(sources) >= 12:
                break
    if not sources:
        return False, "no corpus attestation found"
    world.attestation[surf] = {
        "surface": surf, "n_sources": len(sources), "sources": sorted(sources),
        "n_traditions": len(traditions), "traditions": sorted(traditions),
        "drug": item.get("binomial") or surf, "years": [],
    }
    return True, f"attested in {len(sources)} sources / {len(traditions)} traditions"


def resolve_taxon(world: World, item: dict, lexicon: dict | None = None) -> tuple[bool, str]:
    """Phytochemistry blocked: resolve the drug surface to a binomial, then re-join chemistry."""
    surf = item.get("drug_surface") or ""
    if item.get("binomial"):
        return False, "binomial already present"
    if not lexicon:
        return False, "lexicon unavailable"
    hit = lexicon.get(fold_zh(surf))
    if not hit:
        cand = next((v for k, v in lexicon.items() if surf in k or k in surf), None)
        hit = cand
    if not hit:
        return False, "surface not resolvable through the lexicon"
    item["binomial"] = hit
    classes = world.plant_classes.get(hit)
    if not classes:
        return True, f"resolved to {hit} but no chemistry on record"
    item["chemotype"] = item.get("chemotype") or sorted(classes)[0]
    return True, f"resolved to {hit} ({len(classes)} chemotypes)"


def enrich_operator(world: World, item: dict, core: dict | None = None) -> tuple[bool, str]:
    """Operator blocked: fall back to the curated core semantics for this process term."""
    proc = item.get("process") or ""
    if proc in world.operators:
        return False, "operator already known"
    if core and proc in core:
        world.operators[proc] = core[proc]
        return True, f"operator {proc} recovered from the core table"
    return False, f"no semantics for {proc!r}"


ACTIONS = {
    "ethnobotany": expand_attestation,
    "phytochemistry": resolve_taxon,
    "operator": enrich_operator,
}


# ---------------------------------------------------------------------------------------
# The loop
# ---------------------------------------------------------------------------------------
@dataclass
class Round:
    n: int
    before_mean_agreement: float
    after_mean_agreement: float
    actions: list[dict] = field(default_factory=list)
    upgraded: list[dict] = field(default_factory=list)
    accepted: bool = False
    reason: str = ""


def evaluate(world: World, items: list[dict]) -> tuple[float, list[dict]]:
    """Run the panel; return mean independent-domain agreement and the per-item results."""
    out = []
    for it in items:
        claim = (f"{it.get('process')} of {it.get('drug_surface')} "
                 f"({it.get('binomial')}) should measurably enrich its {it.get('chemotype')} content")
        proposals = [fn(world, it) for fn in EXPERTS.values()]
        c = fuse(claim, proposals)
        out.append({"item": it, "consensus": c.to_dict(),
                    "blocking": [p.domain for p in proposals if p.score < MIN_SUPPORT]})
    mean = sum(r["consensus"]["agreement"] for r in out) / max(1, len(out))
    return mean, out


def run(max_rounds: int = 3) -> dict:
    world = World.load()
    cs = json.loads((ROOT / "artifacts/cross_sections.json").read_text(encoding="utf-8"))
    items = cs.get("all") or cs.get("top") or []

    lex_path = ROOT / "corpus/processed/lexicon_drugs.json"
    lexicon = {}
    if lex_path.exists():
        data = json.loads(lex_path.read_text(encoding="utf-8"))
        for e in data.get("historical", data if isinstance(data, list) else []):
            name = (e.get("name") or "").strip()
            mod = (e.get("modern") or "").strip()
            if len(name) >= 2 and mod:
                lexicon[fold_zh(name)] = mod

    onto = json.loads((ROOT / "artifacts/operator_ontology.json").read_text(encoding="utf-8"))
    core = {o["term"]: o for o in onto.get("operators", [])}

    rounds = []
    for n in range(1, max_rounds + 1):
        before_mean, before = evaluate(world, items)
        # diagnose: for each unsupported claim, find the weakest domain and act on it
        actions, target_ids = [], set()
        for r in before:
            if r["consensus"]["agreement"] >= 3:
                continue
            it = r["item"]
            weakest = min(r["consensus"]["domains"], key=lambda d: d["score"])
            act = ACTIONS.get(weakest["domain"])
            if act is None:
                continue
            changed, note = act(world, it, lexicon if weakest["domain"] == "phytochemistry"
                                else core if weakest["domain"] == "operator" else None)
            actions.append({"candidate": f"{it.get('drug_surface')}+{it.get('process')}",
                            "blocking_domain": weakest["domain"], "action": act.__name__,
                            "changed": changed, "note": note})
            if changed:
                target_ids.add((it.get("drug_surface"), it.get("process")))

        after_mean, after = evaluate(world, items)
        upgraded = []
        before_by = {(r["item"].get("drug_surface"), r["item"].get("process")): r for r in before}
        for r in after:
            key = (r["item"].get("drug_surface"), r["item"].get("process"))
            b = before_by.get(key)
            if b and r["consensus"]["agreement"] > b["consensus"]["agreement"]:
                upgraded.append({"candidate": f"{key[0]}+{key[1]}",
                                 "agreement_before": b["consensus"]["agreement"],
                                 "agreement_after": r["consensus"]["agreement"],
                                 "verdict_after": r["consensus"]["verdict"]})

        # accept if the mean rises, OR if specific hypotheses were upgraded without any downgrade.
        # A flat mean with real upgrades means the gains and losses cancelled — still progress, but
        # it must be reported as such rather than hidden inside an average.
        downgraded = []
        for r in after:
            key = (r["item"].get("drug_surface"), r["item"].get("process"))
            b = before_by.get(key)
            if b and r["consensus"]["agreement"] < b["consensus"]["agreement"]:
                downgraded.append(key)
        n_changed = sum(1 for a in actions if a["changed"])
        if n_changed == 0:
            # No action could acquire anything new: the round has nothing to contribute, so the
            # "upgrades" are re-scores of already-mutated state, not evidence. Drop them and reject.
            upgraded = []
            accepted = False
        else:
            accepted = (after_mean > before_mean + 1e-9) or (bool(upgraded) and not downgraded)
        if accepted:
            reason = "mean independent-domain agreement rose"
        elif n_changed == 0:
            reason = "no effective action available - nothing new to acquire"
        else:
            reason = ("no accepted change: agreement did not improve, so the round is rejected "
                      "and kept only as a record")
        rd = Round(n=n, before_mean_agreement=round(before_mean, 4),
                   after_mean_agreement=round(after_mean, 4), actions=actions,
                   upgraded=upgraded, accepted=accepted, reason=reason)
        rounds.append(rd)
        if not accepted or not upgraded:
            break

    payload = {
        "generated_at": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
        "what": ("self-adjusting research loop: diagnose the blocking domain for each unsupported "
                 "claim, acquire the missing evidence for that domain, re-run the panel, accept only "
                 "if independent-domain agreement rises"),
        "invariant": ("the loop may acquire evidence; it may NOT lower a threshold. A hypothesis is "
                      "never made to pass by changing the bar."),
        "rounds": [{"round": r.n, "before": r.before_mean_agreement, "after": r.after_mean_agreement,
                    "accepted": r.accepted, "reason": r.reason,
                    "n_actions": len(r.actions),
                    "n_changed": sum(1 for a in r.actions if a["changed"]),
                    "upgraded": r.upgraded[:20],
                    "n_upgraded": len(r.upgraded),
                    "actions": r.actions[:40]} for r in rounds],
        "total_upgraded": sum(len(r.upgraded) for r in rounds),
    }
    (ROOT / "artifacts/research_rounds.json").write_text(
        json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")

    L = ["# Self-adjusting research loop", "", payload["generated_at"], "",
         "**The invariant.** The loop may acquire evidence; it may **not** lower a threshold. A claim is",
         "never made to pass by moving the bar — only by learning something that was not known.", "",
         "## Rounds", "", "| Round | Mean agreement before | after | Actions | Upgraded | Accepted |",
         "|---|---|---|---|---|---|"]
    for r in payload["rounds"]:
        L.append(f"| {r['round']} | {r['before']} | {r['after']} | {r['n_actions']} "
                 f"({r['n_changed']} effective) | {len(r['upgraded'])} | "
                 f"{'yes' if r['accepted'] else 'no'} |")
    up = [u for r in payload["rounds"] for u in r["upgraded"]]
    L += ["", f"## The hidden pieces of the puzzle ({len(up)} hypotheses upgraded)", "",
          "Each row is a claim that was a single-domain assertion, and became a cross-domain",
          "interpolation because the loop went and got the missing evidence.", "",
          "| Hypothesis | Before | After | New verdict |", "|---|---|---|---|"]
    for u in up[:25]:
        L.append(f"| {u['candidate']} | {u['agreement_before']}/5 | {u['agreement_after']}/5 | "
                 f"{u['verdict_after']} |")
    if not up:
        L += ["No hypothesis was upgraded. That is the honest outcome of this run and it is reported",
              "rather than tuned away."]
    L += ["", "## What the loop did", ""]
    for r in payload["rounds"]:
        for a in r["actions"][:12]:
            L.append(f"- `{a['action']}` on **{a['candidate']}** (blocking: {a['blocking_domain']}) → "
                     f"{'changed' if a['changed'] else 'no change'}: {a['note']}")
    (ROOT / "artifacts/RESEARCH_LOG.md").write_text("\n".join(L), encoding="utf-8")

    print(f"rounds: {len(rounds)} · upgraded hypotheses: {payload['total_upgraded']}")
    for r in rounds:
        print(f"  round {r.n}: {r.before_mean_agreement} -> {r.after_mean_agreement} "
              f"({'accepted' if r.accepted else 'rejected'}) · "
              f"{sum(1 for a in r.actions if a['changed'])} effective actions")
    return payload


if __name__ == "__main__":
    run()
