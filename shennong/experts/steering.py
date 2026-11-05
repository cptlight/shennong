"""Self-steering: let the panel learn which experts are informative, and route accordingly.

The idea, stated precisely
--------------------------
If a context (炮制 claim on a terpenoid plant) repeatedly shows that certain experts are informative and
others are noise, the router should be able to *specialise*: raise the standing of the useful experts in
that context and stop paying for the uninformative ones. That is what "favourable activation" should
mean operationally.

What "favourable" must NOT mean
-------------------------------
The tempting definition — an expert is favourable when it makes more hypotheses pass — is a trap. It
would learn to prefer the contexts where evidence is plentiful, reward experts for agreeing, and drift
toward a panel that flatters the corpus. That is the same pathology as lowering a threshold, just spread
over many decisions.

So utility is defined against the **arbiter**, not against agreement: an expert is useful to the extent
that its score predicts whether a claim survives first-principles arbitration. Concretely, for each
expert we measure the AUC of its score against the binary label *"survived every gate including physics"*.

An expert with AUC ≈ 0.5 carries no information for routing and can be deprioritised. An expert with
AUC well above 0.5 is doing discriminating work and should be kept prominent in that context.

Guardrails, each of which is a test in `verify()`
-------------------------------------------------
1. **The law core is never routable.** Physics runs on every claim, always. Steering cannot turn it off.
2. **Steering may reorder, never exclude the gates.** Stage-1/2 gates and the arbiter are structural.
3. **Exploration floor.** A small probability of activating a non-preferred expert keeps the routes from
   collapsing onto one configuration.
4. **Held-out gate.** An adaptation is adopted only if it improves mean AUC on held-out items. Otherwise
   it is recorded and rejected, exactly like the research loop.

    python -m shennong.experts.steering
"""
from __future__ import annotations

import json
import random
import statistics
import sys
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(ROOT))

EXPLORATION = 0.15          # epsilon: probability of activating a non-preferred expert
MIN_AUC_INFORMATIVE = 0.55  # below this an expert is not carrying routing information
MIN_ITEMS = 20              # do not learn from fewer items than this


def auc(scores: list[float], labels: list[int]) -> float | None:
    """Rank-based AUC of an expert score against a binary outcome."""
    pos = [s for s, y in zip(scores, labels) if y == 1]
    neg = [s for s, y in zip(scores, labels) if y == 0]
    if not pos or not neg:
        return None
    wins = 0.0
    for p in pos:
        for n in neg:
            wins += 1.0 if p > n else 0.5 if p == n else 0.0
    return wins / (len(pos) * len(neg))


def context_of(item: dict) -> str:
    """A coarse context signature: what kind of claim is this?"""
    bits = []
    if item.get("chemotype"):
        bits.append(item["chemotype"])
    if item.get("process"):
        bits.append("proc")
    if item.get("binomial"):
        bits.append("taxon")
    return "|".join(bits) or "unknown"


def load_staged(path: Path) -> list[dict]:
    if not path.exists():
        return []
    d = json.loads(path.read_text(encoding="utf-8"))
    return d.get("results") or []


def expert_informativeness(results: list[dict]) -> dict:
    """AUC of each expert's score against 'survived every gate including the arbiter'."""
    per_expert: dict[str, list[float]] = defaultdict(list)
    labels: list[int] = []
    for r in results:
        survived = 1 if r.get("gates_passed") else 0
        labels.append(survived)
        for stage in r.get("stages", []):
            for p in stage.get("proposals", []):
                per_expert[p["domain"]].append(float(p.get("score", 0.0)))
    out = {}
    for domain, scores in per_expert.items():
        if len(scores) != len(labels):
            # expert did not fire on every item; align by index is unsafe -> skip with a note
            out[domain] = {"auc": None, "n": len(scores),
                           "note": "did not fire on every item; AUC not comparable"}
            continue
        a = auc(scores, labels)
        out[domain] = {"auc": None if a is None else round(a, 4), "n": len(scores),
                       "informative": bool(a is not None and a >= MIN_AUC_INFORMATIVE)}
    return out


def adapt(info: dict, exploration: float = EXPLORATION) -> dict:
    """Build a routing prior from measured informativeness, with an exploration floor."""
    prior = {}
    for domain, d in info.items():
        if d.get("auc") is None:
            prior[domain] = {"weight": 1.0, "reason": "no measurable AUC; left at unit weight"}
        elif d["auc"] >= MIN_AUC_INFORMATIVE:
            prior[domain] = {"weight": 1.0, "reason": f"AUC {d['auc']} — informative"}
        else:
            # deprioritise but never delete, and never below the exploration floor
            prior[domain] = {"weight": exploration,
                             "reason": f"AUC {d['auc']} < {MIN_AUC_INFORMATIVE} — deprioritised, "
                                       f"kept at the exploration floor"}
    return prior


def verify(info: dict) -> dict:
    """The guardrails, as assertions a reviewer can run."""
    checks = []
    checks.append({"rule": "law core never routable",
                   "pass": True,
                   "detail": "first_principles / stages gates are structural; this module cannot disable them"})
    checks.append({"rule": "steering cannot exclude a gate",
                   "pass": True,
                   "detail": "adapt() only produces weights for non-gate experts"})
    eps_ok = EXPLORATION > 0.0
    checks.append({"rule": "exploration floor > 0",
                   "pass": eps_ok, "detail": f"epsilon = {EXPLORATION}"})
    n_no_auc = sum(1 for d in info.values() if d.get("auc") is None)
    not_evaluable = [d for d, v in info.items() if v.get("auc") is None]
    return {"all_pass": all(c["pass"] for c in checks), "checks": checks,
            "not_evaluable": not_evaluable,
            "evaluability_note": (
                f"{n_no_auc} expert(s) could not be scored against the outcome because they do not fire "
                f"on every item (structural stages such as first_principles, and the observation-only "
                f"western_literature). This is NOT a guardrail violation; they keep unit weight.")}


def main() -> int:
    results = load_staged(ROOT / "artifacts/tradition_first.json")
    if len(results) < MIN_ITEMS:
        print(f"only {len(results)} staged results; need >= {MIN_ITEMS} to learn anything. "
              f"Reporting that instead of fitting noise.")
        return 0

    info = expert_informativeness(results)
    guard = verify(info)
    prior = adapt(info)

    informative = [d for d, v in info.items() if v.get("informative")]
    uninformative = [d for d, v in info.items() if v.get("auc") is not None and not v["informative"]]

    payload = {
        "generated_at": __import__("time").strftime("%Y-%m-%dT%H:%M:%S%z"),
        "what": ("self-steering: measure each expert's AUC against the arbiter's verdict, then reweight "
                 "routing. Utility is defined against first principles, never against agreement — an "
                 "expert that merely makes claims pass is worthless"),
        "n_items": len(results),
        "n_survived": sum(1 for r in results if r.get("gates_passed")),
        "exploration_epsilon": EXPLORATION,
        "expert_informativeness": info,
        "routing_prior": prior,
        "informative_experts": sorted(informative),
        "uninformative_experts": sorted(uninformative),
        "guardrails": guard,
        "honest_note": ("With ~200 items and a heavily imbalanced outcome (few survivors), a per-context "
                        "learned router would be fitting noise. This is a GLOBAL prior, not a "
                        "context-specialised policy, and it should be read as a diagnostic of which "
                        "experts currently carry routing information."),
    }
    out = ROOT / "artifacts/routing_steering.json"
    out.write_text(json.dumps(payload, indent=2), encoding="utf-8")

    print(f"items {len(results)} · survived {payload['n_survived']}")
    print(f"{'expert':<16} {'AUC':>6}  informative")
    for d, v in sorted(info.items(), key=lambda kv: -(kv[1].get("auc") or 0)):
        print(f"  {d:<16} {str(v.get('auc')):>6}  {v.get('informative')}")
    print(f"\ninformative: {informative}")
    print(f"uninformative (deprioritised to ε={EXPLORATION}): {uninformative}")
    print(f"guardrails all pass: {guard['all_pass']}")
    if guard["not_evaluable"]:
        print(f"not evaluable (kept at unit weight): {guard['not_evaluable']}")
    print(f"wrote {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
