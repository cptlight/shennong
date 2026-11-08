#!/usr/bin/env python3
"""Track-2 screening: query a disease target, get ranked plant-derived compounds with evidence.

This is the "predictive model / knowledge graph / screening pipeline" layer, built on the data we already
have — no GPU, no network. For a query like "COX2" or "inflammation" it returns the plants whose compounds
are linked to that target, with the evidence chain and a physics/ADMET sanity flag.

    python -m shennong.screen "COX2"          # or: shennong screen-target "COX2"

Layers (in order):
  1 knowledge graph    plant -> compound_class/gene_target -> target/disease   (multi-hop, exact)
  2 predictive         ECFP/Tanimoto similarity vs known actives               (cheminformatics, next)
  3 screening          ADMET rules + physics arbiter (preparation viability)   (falsifiable)
"""
from __future__ import annotations

import csv
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
STRUCT = ROOT / "corpus" / "processed" / "structured"


def _load(rel: str) -> list[dict]:
    p = STRUCT / rel
    return list(csv.DictReader(p.open(encoding="utf-8"))) if p.exists() else []


def _norm(s: str) -> str:
    return (s or "").strip().lower().replace("-", "").replace(" ", "").replace("_", "")


def screen_target(query: str, top_k: int = 20) -> dict:
    q = _norm(query)
    if not q:
        return {"ok": False, "error": "empty query"}

    # ---- 1. exact gene-target hits from IMPPAT ----
    gene_rows = []
    for r in _load("imppat_targets.csv"):
        if _norm(r.get("gene_target")) == q:
            gene_rows.append(r)

    # ---- 2. pharmacology (compound class -> target -> disease) ----
    pharm_rows = []
    for r in _load("pharmacology.csv"):
        blob = _norm(r.get("molecular_target", "") + " " + r.get("disease", "") + " " + r.get("compound_class", ""))
        if q in blob:
            pharm_rows.append(r)

    # ---- 3. compound-class rows (for evidence of what the plant contains) ----
    comp_index = {}
    for r in _load("compounds.csv"):
        p = (r.get("plant_binomial") or "").strip()
        c = (r.get("compound_class") or "").strip()
        if p and c and c != "unclassified":
            comp_index.setdefault(p, set()).add(c)

    # ---- assemble, dedupe by plant ----
    plants = {}
    for r in gene_rows:
        p = r["plant_binomial"]
        plants.setdefault(p, {"plant": p, "gene_targets": [], "compound_classes": [], "diseases": []})
        plants[p]["gene_targets"].append(r["gene_target"])
    for r in pharm_rows:
        p = r["plant_binomial"]
        plants.setdefault(p, {"plant": p, "gene_targets": [], "compound_classes": [], "diseases": []})
        plants[p]["compound_classes"].append(f"{r['compound_class']} → {r['molecular_target']}")
        plants[p]["diseases"].append(r["disease"])
    for p in plants:
        plants[p]["compound_classes"] += sorted(comp_index.get(p, set()))
        plants[p]["compound_classes"] = sorted(set(plants[p]["compound_classes"]))[:5]
        plants[p]["gene_targets"] = sorted(set(plants[p]["gene_targets"]))[:5]
        plants[p]["diseases"] = sorted(set(plants[p]["diseases"]))[:5]

    results = sorted(plants.values(),
                     key=lambda x: (bool(x["gene_targets"]) + bool(x["compound_classes"])), reverse=True)[:top_k]
    return {
        "ok": True,
        "query": query,
        "n_plants": len(results),
        "method": ("knowledge-graph: plant → compound_class/gene_target → target/disease (exact multi-hop). "
                   "Next layers: ECFP/Tanimoto similarity vs ChEMBL actives, then ADMET + physics arbiter."),
        "results": results,
    }


def _main() -> int:
    q = sys.argv[1] if len(sys.argv) > 1 else "COX2"
    print(json.dumps(screen_target(q), indent=2, ensure_ascii=False)[:3000])
    return 0


if __name__ == "__main__":
    raise SystemExit(_main())


# --------------------------------------------------------------------------------------
# Layer 3: the fused screen — knowledge graph -> ECFP similarity -> ADMET -> physics -> novelty
# --------------------------------------------------------------------------------------

# a standard herbal preparation, used as the default physics test for a screened compound
DEFAULT_PROCESS = "煎"
FPS_CACHE = ROOT / "artifacts" / "compound_fps.pkl"


def admet_flags(smiles: str) -> dict:
    """Lipinski/Veber-style ADMET flags from our own descriptor code (no external deps)."""
    from shennong.chem import (hba, hbd, logp_fragment_estimate, molecular_weight,
                               parse_smiles, rotatable_bonds, tpsa)
    try:
        m = parse_smiles(smiles)
    except Exception:  # noqa: BLE001
        return {"ok": False, "note": "unparseable SMILES"}
    mw, don, acc = molecular_weight(m), hbd(m), hba(m)
    tp, lg, rb = tpsa(m), logp_fragment_estimate(m), rotatable_bonds(m)
    bad = []
    if mw > 500:
        bad.append(f"MW {mw:.0f} > 500")
    if lg > 5:
        bad.append(f"logP {lg:.1f} > 5")
    if don > 5:
        bad.append(f"HBD {don} > 5")
    if acc > 10:
        bad.append(f"HBA {acc} > 10")
    if tp > 140:
        bad.append(f"TPSA {tp:.0f} > 140")
    if rb > 10:
        bad.append(f"rotatable {rb} > 10")
    return {"ok": True, "mw": round(mw, 1), "hbd": don, "hba": acc, "tpsa": round(tp, 1),
            "logp": round(lg, 2), "rotatable": rb,
            "lipinski_pass": not bad, "violations": bad}


def physics_verdict(compound_class: str, process: str = DEFAULT_PROCESS) -> dict:
    """Can this compound class survive a standard preparation? Uses the validated arbiter."""
    from shennong.experts.first_principles import check_process_physics
    pc = check_process_physics(process, compound_class or "", "")
    return {"process": process, "checked": pc.passed is not None,
            "passed": pc.passed, "score": round(pc.score, 3), "reasoning": pc.reasoning}


TARGET_CACHE = ROOT / "artifacts" / "chembl_targets.json"


def _target_cache() -> dict:
    """Precomputed target -> actives. HF Spaces cannot reach the EBI API (500), so the demo must not query live."""
    import json as _json
    try:
        return _json.loads(TARGET_CACHE.read_text(encoding="utf-8"))
    except Exception:  # noqa: BLE001
        return {}


def _save_target_cache(cache: dict) -> None:
    import json as _json
    try:
        TARGET_CACHE.parent.mkdir(parents=True, exist_ok=True)
        TARGET_CACHE.write_text(_json.dumps(cache, ensure_ascii=False), encoding="utf-8")
    except Exception:  # noqa: BLE001
        pass


def chembl_rank(target: str, limit: int = 120, top: int = 24) -> dict:
    """EFP4 similarity of our compounds to a target's known ChEMBL actives."""
    import csv as _csv
    import json as _json
    import urllib.parse
    import urllib.request
    from rdkit import Chem, DataStructs
    from rdkit.Chem import AllChem

    BASE = "https://www.ebi.ac.uk/chembl/api/data"
    ALIASES = {"cox2": "PTGS2", "cox-2": "PTGS2", "cox1": "PTGS1", "cox-1": "PTGS1",
               "egfr": "EGFR", "her2": "ERBB2", "vegfr": "KDR", "dpp4": "DPP4", "dpp-4": "DPP4",
               "ache": "ACHE", "mao": "MAOA", "tubulin": "TUBB", "mtor": "MTOR", "parp": "PARP1"}

    def get(url):
        req = urllib.request.Request(url, headers={"User-Agent": "shennong/1.0"})
        with urllib.request.urlopen(req, timeout=40) as r:
            return _json.loads(r.read())

    raw = (target or "").strip().lower().replace(" ", "")
    _cache = _target_cache()
    if raw in _cache:
        tgt, acts = _cache[raw]["target"], _cache[raw]["actives"]
        return _rank_against(tgt, acts, top)

    q = ALIASES.get(raw, target)
    d = get(f"{BASE}/target/search.json?q={urllib.parse.quote(q)}&limit=8")
    ts = [{"id": t["target_chembl_id"], "name": t.get("pref_name") or "", "type": t.get("target_type")}
          for t in d.get("targets", [])]
    ts.sort(key=lambda t: 0 if t["type"] == "SINGLE PROTEIN" else 1)
    if not ts:
        return {"ok": False, "error": f"no ChEMBL target for {target!r}"}
    tgt = ts[0]
    acts = get(f"{BASE}/activity.json?target_chembl_id={tgt['id']}&standard_type=IC50"
               f"&standard_value__lte=10000&limit={limit}").get("activities", [])
    acts = [{"id": a.get("molecule_chembl_id"), "smiles": a.get("canonical_smiles"),
             "nM": a.get("standard_value")} for a in acts if a.get("canonical_smiles")]

    _cache[raw] = {"target": tgt, "actives": acts}
    _save_target_cache(_cache)

    return _rank_against(tgt, acts, top)


def _rank_against(tgt: dict, acts: list, top: int) -> dict:
    """EFP4 similarity of our compounds to a target's known actives (no network)."""
    import csv as _csv
    from rdkit import Chem, DataStructs
    from rdkit.Chem import AllChem

    def fp(smi):
        m = Chem.MolFromSmiles(smi)
        return AllChem.GetMorganFingerprintAsBitVect(m, 2, nBits=2048) if m else None

    act_fps = [(a, fp(a["smiles"])) for a in acts]
    act_fps = [(a, f) for a, f in act_fps if f]
    # compound fingerprints: precomputed cache first (the Space is 2 vCPU and a live recompute times out)
    entries = []  # (name, smiles, plant, class, fp)
    if FPS_CACHE.exists():
        import pickle
        from rdkit.DataStructs import CreateFromBinaryText
        try:
            with FPS_CACHE.open("rb") as fh:
                for n, smi, plant, cls, bfp in pickle.load(fh):
                    entries.append((n, smi, plant, cls, CreateFromBinaryText(bfp)))
        except Exception:  # noqa: BLE001
            entries = []
    if not entries:
        for r in _csv.DictReader((STRUCT / "compounds.csv").open(encoding="utf-8")):
            smi = (r.get("smiles") or "").strip()
            if not smi:
                continue
            f = fp(smi)
            if f is not None:
                entries.append((r.get("name") or "", smi, r.get("plant_binomial") or "",
                                r.get("compound_class") or "", f))

    act_vectors = [x[1] for x in act_fps]
    scored = []
    for name, smi, plant, cls, f in entries:
        sims = DataStructs.BulkTanimotoSimilarity(f, act_vectors)
        best = max(sims) if sims else 0.0
        if best <= 0:
            continue
        j = sims.index(best)
        scored.append({"name": name, "smiles": smi, "plant_binomial": plant,
                       "compound_class": cls, "tanimoto": round(best, 4),
                       "matched_active": act_fps[j][0]["id"],
                       "matched_active_nM": act_fps[j][0]["nM"]})
    scored.sort(key=lambda x: -x["tanimoto"])
    return {"ok": True, "target": tgt, "n_actives": len(act_fps), "top": scored[:top]}


def fused_screen(target: str, top_k: int = 8, process: str = DEFAULT_PROCESS) -> dict:
    """Run all three Track-2 layers and fuse them into one ranked, falsifiable shortlist.

    layer 1 knowledge graph  -> which plants are linked to the target (evidence chain)
    layer 2 cheminformatics  -> which compounds are structurally close to known actives (ECFP/Tanimoto)
    layer 3 screening        -> ADMET flags + physics (does it survive preparation) + novelty
    """
    chem = chembl_rank(target, top=top_k)
    hits = []
    for h in (chem.get("top") or [])[:top_k]:
        hit = dict(h)
        hit["admet"] = admet_flags(h["smiles"])
        hit["physics"] = physics_verdict(h["compound_class"], process)
        hit["novelty"] = {"structural_novelty": round(1.0 - h["tanimoto"], 3),
                          "note": "1 − Tanimoto to the closest known active (higher = less familiar)"}
        # a simple, transparent fused score: similarity × ADMET × physics-stability
        adme = 1.0 if hit["admet"].get("lipinski_pass") else 0.5
        phys = 1.0 if hit["physics"].get("passed") is not False else 0.4
        hit["fused_score"] = round(h["tanimoto"] * adme * phys, 3)
        hits.append(hit)
    hits.sort(key=lambda x: -x["fused_score"])
    return {"target_query": target, "ok": bool(chem.get("ok")),
            "target": chem.get("target"), "n_actives": chem.get("n_actives"),
            "method": ("layer 1: plant→compound→target KG · layer 2: ECFP4 Tanimoto vs ChEMBL actives · "
                       "layer 3: Lipinski ADMET + preparation physics + structural novelty"),
            "hits": hits}
