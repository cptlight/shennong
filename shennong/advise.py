#!/usr/bin/env python3
"""Route a free-text question to the experts it needs, and have each one return a verdict.

This is the "understand the request and route it to the appropriate expert" behaviour:

    1. the semantic router fires the experts the question actually needs (plant name -> taxonomy,
       chemotaxonomy, phytochemistry; "toxic"/"dose" -> toxicology, adme; "process"/"炮" -> operator,
       extraction; classical-property language -> theory; mechanism language -> mechanics, quantum, microbiome)
    2. the question is parsed into (drug, process, chemotype) and era-mapped to a binomial
    3. every activated expert returns a Proposal — a score, a rationale, and its evidence
    4. the proposals are fused into a consensus, and the physics arbiter rules when a process is present

    python -m shennong.advise "Is 附子 toxic, and does 炮 reduce that?"
"""
from __future__ import annotations

import json
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from shennong.experts.router import route_query  # noqa: E402

_PROCESS_TERMS = ("炮", "蒸", "煮", "煎", "炒", "煅", "浸", "焙", "炙", "煨", "蜜炙", "醋炙", "炒焦", "炒炭")
_CHEMO_TERMS = ("alkaloid", "terpenoid", "flavonoid", "glycoside", "phenylpropanoid", "polyketide",
                "steroid", "saponin", "organosulfur", "volatile oil", "polysaccharide")

_WORLD = {"w": None}
_RESOLVED = {"m": None}


def _world():
    if _WORLD["w"] is None:
        from shennong.experts import World
        _WORLD["w"] = World.load()
    return _WORLD["w"]


def _resolved() -> dict:
    if _RESOLVED["m"] is None:
        p = ROOT / "corpus/processed/lexicon_drugs.json"
        try:
            lex = json.loads(p.read_text(encoding="utf-8"))
            _RESOLVED["m"] = {r["name"]: r["modern"] for r in lex.get("historical", []) if r.get("name")}
        except Exception:  # noqa: BLE001
            _RESOLVED["m"] = {}
    return _RESOLVED["m"]


def _parse(question: str) -> dict:
    q = question or ""
    process = next((t for t in _PROCESS_TERMS if t in q), "")
    chemotype = next((t for t in _CHEMO_TERMS if t.lower() in q.lower()), "")
    resolved = _resolved()
    drug = next((n for n in sorted(resolved, key=len, reverse=True) if n and n in q), "")
    return {"drug": drug, "process": process, "chemotype": chemotype,
            "binomial": resolved.get(drug, "") if drug else ""}


def advise(question: str) -> dict:
    """Route the question, run every activated expert, and return their verdicts."""
    q = (question or "").strip()
    if not q:
        return {"ok": False, "error": "empty question"}

    routed = route_query(q)
    parsed = _parse(q)

    from shennong.experts import EXPERTS, fuse
    item = {"drug_surface": parsed["drug"] or "(unnamed)",
            "process": parsed["process"], "chemotype": parsed["chemotype"],
            "binomial": parsed["binomial"]}

    w = _world()
    feedback, proposals = [], []
    for name in routed["experts"]:
        fn = EXPERTS.get(name)
        if fn is None:
            continue
        try:
            p = fn(w, item)
        except Exception as exc:  # noqa: BLE001
            feedback.append({"expert": name, "score": None, "rationale": f"unavailable: {type(exc).__name__}"})
            continue
        proposals.append(p)
        feedback.append({"expert": name, "score": round(float(p.score), 3),
                         "rationale": (p.rationale or "")[:400],
                         "evidence": list(p.evidence or [])[:4]})

    consensus = {}
    if proposals:
        try:
            c = fuse(q, proposals)
            consensus = {"n_supporting": int(c.agreement), "n": len(proposals),
                         "label": f"{int(c.agreement)}/{len(proposals)} expert domains support the reading",
                         "score": round(float(c.consensus_score), 3),
                         "verdict": c.verdict,
                         "disagreements": [d[:200] for d in (c.disagreements or [])[:3]]}
        except Exception:  # noqa: BLE001
            consensus = {"n": len(proposals)}

    out = {"ok": True, "question": q, "parsed": parsed,
           "routed": {"n_active": routed["n_active"], "experts": routed["experts"],
                      "why": routed["why"], "features": routed["features"]},
           "feedback": feedback, "consensus": consensus}

    # physics arbiter, when the question names a preparation and a compound class
    if parsed["process"] or parsed["chemotype"]:
        try:
            from shennong.experts.first_principles import arbitrate
            out["arbiter"] = arbitrate(parsed["process"], parsed["chemotype"], None, q)
        except Exception as exc:  # noqa: BLE001
            out["arbiter"] = {"error": f"{type(exc).__name__}: {exc}"}
    return out


def _main() -> int:
    q = " ".join(sys.argv[1:]) or "Is 附子 toxic, and does 炮 reduce that?"
    print(json.dumps(advise(q), indent=2, ensure_ascii=False)[:4000])
    return 0


if __name__ == "__main__":
    raise SystemExit(_main())
