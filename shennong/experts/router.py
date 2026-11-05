"""Expert router — activate only the experts a given item can actually use.

The panel is now twelve experts. Running all twelve on every item would be wasteful and, worse,
*noisy*: an ADME question is meaningless for a mineral, and a steam-volatility argument is meaningless
for a polysaccharide. Routing is therefore done on **content features of the item**, not on a learned
gate, because the features that make an expert applicable are known exactly:

| feature present in the item | experts it activates |
|---|---|
| a binomial | taxonomy, chemotaxonomy, phytochemistry |
| a structure (SMILES) | mechanics, quantum, adme |
| a 炮制 process term | operator, extraction |
| a toxicity marking or alert | toxicology |
| a classical property vector | theory |
| a glycosidic chemotype | microbiome |
| (always) | ethnobotany — the record question applies to everything |

This is the same sparsity principle as the neural MoE, one level up: the FFN experts are routed by a
learned gate inside the model, the *tool* experts are routed by lexical/schema features outside it. Both
keep activation proportional to what the item can use.

    python -m shennong.experts.router        # report the activation distribution
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(ROOT))

ALWAYS = ("ethnobotany",)

RULES = {
    "binomial": ("taxonomy", "chemotaxonomy", "phytochemistry"),
    "structure": ("mechanics", "quantum", "adme"),
    "process": ("operator", "extraction"),
    "toxicity": ("toxicology",),
    "properties": ("theory",),
    "glycoside": ("microbiome",),
}


def features(item: dict) -> set[str]:
    """Which capability-features does this item actually carry?"""
    f: set[str] = set()
    if item.get("binomial"):
        f.add("binomial")
    if item.get("chemotype"):
        f.add("structure")          # a chemotype implies a representative structure exists
    if item.get("process"):
        f.add("process")
    if "tox" in (item.get("chemotype") or "").lower() or item.get("toxic"):
        f.add("toxicity")
    if item.get("theory") or item.get("nature") or item.get("properties"):
        f.add("properties")
    if (item.get("chemotype") or "").lower() in ("glycoside", "flavonoid", "polysaccharide"):
        f.add("glycoside")
    return f


def route(item: dict) -> list[str]:
    """Return the ordered list of experts to activate for this item."""
    active = list(ALWAYS)
    for feat in features(item):
        for exp in RULES.get(feat, ()):
            if exp not in active:
                active.append(exp)
    return active


def report(items: list[dict]) -> dict:
    counts: dict[str, int] = {}
    per_item: list[int] = []
    combos: dict[str, int] = {}
    for it in items:
        active = route(it)
        per_item.append(len(active))
        for e in active:
            counts[e] = counts.get(e, 0) + 1
        key = "+".join(active)
        combos[key] = combos.get(key, 0) + 1
    n = len(items) or 1
    return {
        "n_items": len(items),
        "n_experts_total": 12,
        "mean_active_per_item": round(sum(per_item) / n, 2),
        "max_active_per_item": max(per_item) if per_item else 0,
        "activation_fraction": round(sum(per_item) / (n * 12), 3),
        "per_expert_activation": dict(sorted(counts.items(), key=lambda kv: -kv[1])),
        "distinct_routes": len(combos),
        "top_routes": dict(sorted(combos.items(), key=lambda kv: -kv[1])[:5]),
    }


def mixed_stream(limit: int = 300) -> list[dict]:
    """A realistic ingestion stream: rich structured items mixed with plain corpus text.

    Real source data is heterogeneous — most chunks carry no binomial, no process, and no structure.
    Routing a flat panel over this stream is what the router exists to avoid.
    """
    out: list[dict] = []
    cs = json.loads((ROOT / "artifacts/cross_sections.json").read_text(encoding="utf-8"))
    out.extend((cs.get("all") or cs.get("top") or [])[:60])
    try:
        inc = list(__import__("csv").DictReader(
            open(ROOT / "corpus/processed/structured/incompatibilities.csv", encoding="utf-8")))
        for r in inc:
            out.append({"drug_surface": r.get("drug_a"), "process": None, "binomial": None,
                        "chemotype": None, "rule_system": r.get("rule_system")})
    except Exception:  # noqa: BLE001
        pass
    corpus = ROOT / "corpus/processed/corpus.jsonl"
    if corpus.exists():
        n = 0
        with corpus.open(encoding="utf-8") as fh:
            for line in fh:
                line = line.strip()
                if not line:
                    continue
                try:
                    rec = json.loads(line)
                except json.JSONDecodeError:
                    continue
                out.append({"text": (rec.get("text") or "")[:200], "source_id": rec.get("source_id")})
                n += 1
                if n >= limit:
                    break
    return out


# ---------------------------------------------------------------------------------------
# Conversation-level routing: activate experts for a QUESTION, not just a record
# ---------------------------------------------------------------------------------------
QUERY_CUES = {
    "process": ("炮", "蒸", "煮", "炒", "炙", "煅", "煨", "淬", "飞", "伏", "浸", "渍", "煎",
                "processing", "process", "prepare", "preparation", "decoct", "fry", "roast"),
    "theory": ("性", "味", "歸經", "归经", "寒", "熱", "热", "溫", "温", "涼", "凉", "rasa", "virya",
               "vīrya", "guna", "guṇa", "channel", "nature", "flavour", "flavor"),
    "toxicity": ("毒", "tox", "poison", "safe", "safety", "danger", "side effect", "adverse"),
    "dose": ("dose", "dosage", "dosing", "how much", "mg", "g ", "錢", "两", "兩", "分"),
    "mechanism": ("why", "how does", "mechanism", "target", "receptor", "pathway", "enzyme",
                  "為甚麼", "为什么", "機理", "机理"),
    "structure": ("smiles", "structure", "molecule", "compound", "chemical", "分子", "化合物"),
    "rule": ("十八反", "十九畏", "incompatib", "viruddha", "contraindicat", "禁忌"),
    "tradition": ("tcm", "ayurveda", "unani", "kampo", "tibetan", "tcm", "中醫", "中医", "阿育吠陀"),
}


def route_query(question: str) -> dict:
    """Pick the experts a natural-language question actually needs."""
    q = (question or "").lower()
    active: list[str] = list(ALWAYS)
    reasons: dict[str, str] = {"ethnobotany": "every question is first a question about the record"}

    latin = __import__("re").findall(r"\b[A-Z][a-z]+\s+[a-z]{3,}\b", question or "")
    cjk_drug = __import__("re").findall(r"[\u4e00-\u9fff]{2,4}", question or "")
    if latin or len(cjk_drug) >= 1:
        for e, why in (("taxonomy", "a plant name was detected"),
                       ("chemotaxonomy", "a plant name was detected"),
                       ("phytochemistry", "a plant name was detected")):
            if e not in active:
                active.append(e); reasons[e] = why

    triggered = {}
    for feature, cues in QUERY_CUES.items():
        if any(c in q for c in cues):
            triggered[feature] = True
    if triggered.get("process"):
        for e in ("operator", "extraction"):
            if e not in active:
                active.append(e); reasons[e] = "the question concerns a preparation"
    if triggered.get("theory"):
        if "theory" not in active:
            active.append("theory"); reasons["theory"] = "the question invokes classical properties"
    if triggered.get("toxicity"):
        if "toxicology" not in active:
            active.append("toxicology"); reasons["toxicology"] = "safety language detected"
    if triggered.get("dose") or triggered.get("toxicity"):
        if "adme" not in active:
            active.append("adme"); reasons["adme"] = "dose/safety implies exposure reasoning"
    if triggered.get("mechanism"):
        for e in ("quantum", "mechanics", "microbiome"):
            if e not in active:
                active.append(e); reasons[e] = "a mechanism question needs physical reasoning"
    if triggered.get("structure"):
        for e in ("mechanics", "quantum", "adme"):
            if e not in active:
                active.append(e); reasons[e] = "a structural question"
    if triggered.get("rule"):
        if "toxicology" not in active:
            active.append("toxicology"); reasons["toxicology"] = "an incompatibility rule was named"

    return {"question": question, "n_active": len(active), "experts": active,
            "why": reasons, "features": sorted(triggered)}


if __name__ == "__main__":
    cs = json.loads((ROOT / "artifacts/cross_sections.json").read_text(encoding="utf-8"))
    items = cs.get("all") or cs.get("top") or []
    r = report(items)
    print(f"items {r['n_items']}  experts {r['n_experts_total']}  "
          f"mean active/item {r['mean_active_per_item']}  "
          f"fraction of full panel {r['activation_fraction']:.1%}  "
          f"distinct routes {r['distinct_routes']}")
    print("per-expert activation:")
    for k, v in r["per_expert_activation"].items():
        print(f"  {k:<14} {v:>4}  ({v / r['n_items']:.0%} of items)")
    print("top routes:")
    for k, v in r["top_routes"].items():
        print(f"  {v:>4}  {k}")

    mixed = mixed_stream()
    rm = report(mixed)
    print()
    print(f"MIXED STREAM: items {rm['n_items']}  mean active/item {rm['mean_active_per_item']}  "
          f"fraction of full panel {rm['activation_fraction']:.1%}  "
          f"distinct routes {rm['distinct_routes']}")
    for k, v in list(rm["top_routes"].items())[:4]:
        print(f"  {v:>4}  {k}")
    demo = ["Why is 附子 processed before use?",
            "Does 甘草 taste sweet and enter the heart channel?",
            "Is the 十八反 rule about 烏頭 and 半夏 real?",
            "What dose of 麻黃 is safe?",
            "How does berberine reach its target?"]
    print()
    print("CONVERSATION ROUTING")
    for qq in demo:
        rq = route_query(qq)
        print(f"  {rq['n_active']:>2} experts | {qq[:52]:<52} -> {', '.join(rq['experts'][:5])}")

    out = ROOT / "artifacts/expert_routing.json"
    out.write_text(json.dumps({"flat_panel": r, "mixed_stream": rm}, indent=2), encoding="utf-8")
    print(f"wrote {out}")
