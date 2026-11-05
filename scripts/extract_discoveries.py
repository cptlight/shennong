#!/usr/bin/env python3
"""Extract novel, checkable findings from 45.6 M characters of classical Asian medicine.

Three findings that only exist because the whole corpus is read at once. Each is a **property of the
corpus**, not a sentence generated about a plant — which is what the earlier template pass got wrong.

**F1 — Cross-tradition convergence.** The same drug surface independently attested in ≥2 traditions
(TCM / Ayurveda / Unani / Kampo / Tibetan). Independent traditions are quasi-independent observations,
so agreement between them is a stronger efficacy prior than any single book.

**F2 — Unevidenced single-attestation knowledge.** A drug surface whose entire textual record is one
source out of 106. This is the preservation argument computed from the record instead of asserted: it
names what to digitise and translate before it disappears.

**F3 — Orphan procedures.** A 炮制 step attested for a drug in exactly one text while the drug is
otherwise documented across several. Candidate "lost methods" — procedures that were not transmitted.

**F4 — Multi-source corroboration.** Drug surfaces attested in many independent sources: the stable
core of the tradition, and the safest place to start a screening campaign.

Why text-level and not `uses.csv`: the structured join covers 5,084 of 11,819 use-records, **all from
one source** (`ws_zh_bencao_gangmu`), and some joined binomials are not plants at all (Wikidata false
joins — *Phycodurus eques*, a seahorse). Any "source diversity" statistic computed from that table is
an artifact. Scanning the corpus directly for lexicon surfaces across 106 sources is cruder about
synonymy but it is not contaminated, so that is what this script reports.

    python scripts/extract_discoveries.py
"""
from __future__ import annotations

import argparse
import csv
import json
import sys
import time
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))


def load_lexicon(path: Path) -> dict[str, str]:
    from shennong.normalize import fold_zh
    data = json.loads(path.read_text(encoding="utf-8"))
    entries = data.get("historical", data if isinstance(data, list) else [])
    out: dict[str, str] = {}
    for e in entries:
        name = (e.get("name") or "").strip()
        if len(name) < 2:
            continue
        out[fold_zh(name)] = e.get("modern") or name
    return out


def scan(corpus: Path, surfaces: dict[str, str]):
    """surface -> sets of sources / traditions / years, over the whole corpus, one pass."""
    from shennong.normalize import fold_zh
    keys = sorted(surfaces, key=len, reverse=True)
    src: dict[str, set[str]] = defaultdict(set)
    trad: dict[str, set[str]] = defaultdict(set)
    yrs: dict[str, set[int]] = defaultdict(set)
    n_chunks = 0
    with corpus.open(encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if not line:
                continue
            try:
                rec = json.loads(line)
            except json.JSONDecodeError:
                continue
            text = fold_zh(rec.get("text") or "")
            if not text:
                continue
            hit = [k for k in keys if k in text]
            if not hit:
                continue
            n_chunks += 1
            sid = rec.get("source_id") or ""
            tr = rec.get("tradition") or ""
            yr = rec.get("year")
            for h in hit[:40]:
                src[h].add(sid)
                if tr:
                    trad[h].add(tr)
                if isinstance(yr, int):
                    yrs[h].add(yr)
    return src, trad, yrs, n_chunks


def load_processing(path: Path) -> list[dict]:
    rows = []
    with path.open(encoding="utf-8") as fh:
        for r in csv.DictReader(fh):
            drug = (r.get("drug_name") or "").strip()
            proc = (r.get("process_term") or "").strip()
            if not (drug and proc):
                continue
            if len(drug) < 2 or "*" in drug:
                continue
            if not any("\u4e00" <= ch <= "\u9fff" for ch in drug):
                continue
            rows.append({"drug": drug, "process": proc,
                         "modern": (r.get("process_modern") or "").strip(),
                         "effect": (r.get("effect") or "").strip(),
                         "source": (r.get("source_id") or "").strip()})
    return rows


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--corpus", default="corpus/processed/corpus.jsonl")
    ap.add_argument("--lexicon", default="corpus/processed/lexicon_drugs.json")
    ap.add_argument("--processing", default="corpus/processed/structured/processing.csv")
    ap.add_argument("--out-json", default="artifacts/discoveries.json")
    ap.add_argument("--out-md", default="artifacts/DISCOVERIES.md")
    ap.add_argument("--top", type=int, default=20)
    args = ap.parse_args()

    surfaces = load_lexicon(ROOT / args.lexicon)
    print(f"{len(surfaces):,} lexicon surfaces", flush=True)
    t0 = time.time()
    src, trad, yrs, n_chunks = scan(ROOT / args.corpus, surfaces)
    print(f"scanned {n_chunks:,} chunks with a drug mention in {time.time() - t0:.0f}s; "
          f"{len(src):,} surfaces attested", flush=True)

    procs = load_processing(ROOT / args.processing)
    all_sources = {s for v in src.values() for s in v}
    n_sources = len(all_sources)

    def row(surf: str) -> dict:
        return {"surface": surf, "drug": surfaces[surf],
                "n_sources": len(src[surf]), "sources": sorted(src[surf])[:8],
                "traditions": sorted(trad[surf]),
                "n_traditions": len(trad[surf]),
                "years": sorted(yrs[surf])[:5]}

    rows = [row(s) for s in src]
    # F1: convergence across >=2 traditions
    convergence = [r for r in rows if r["n_traditions"] >= 2]
    convergence.sort(key=lambda r: (r["n_traditions"], r["n_sources"]), reverse=True)
    # F2: single-source record
    single = [r for r in rows if r["n_sources"] == 1]
    single.sort(key=lambda r: r["surface"], reverse=True)
    # F4: corroborated core
    corroborated = [r for r in rows if r["n_sources"] >= 20]
    corroborated.sort(key=lambda r: r["n_sources"], reverse=True)

    # F3: orphan procedures
    ps: dict[tuple[str, str], set[str]] = defaultdict(set)
    pm: dict[tuple[str, str], dict] = {}
    for p in procs:
        ps[(p["drug"], p["process"])].add(p["source"])
        pm.setdefault((p["drug"], p["process"]), p)
    drug_proc_sources = Counter()
    for (drug, _), s_ in ps.items():
        drug_proc_sources[drug] += len(s_)
    orphans = [{"drug": d, "process": pr, "modern": pm[(d, pr)]["modern"],
                "effect": pm[(d, pr)]["effect"], "source": sorted(s)[0],
                "drug_total_process_sources": drug_proc_sources[d]}
               for (d, pr), s in ps.items() if len(s) == 1 and drug_proc_sources[d] >= 2]
    orphans.sort(key=lambda o: o["drug_total_process_sources"], reverse=True)

    payload = {
        "generated_at": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
        "method": ("one pass over corpus.jsonl; every lexicon drug-surface is matched per chunk and "
                   "attributed to its source, tradition and year. Text-level so source diversity is "
                   "not an artifact of the (single-source) structured join."),
        "corpus": {"chunks_with_drug_mention": n_chunks, "sources_seen": n_sources,
                   "surfaces_in_lexicon": len(surfaces), "surfaces_attested": len(src)},
        "findings": {
            "F1_cross_tradition_convergence": {
                "definition": "surface attested in >=2 traditions — quasi-independent corroboration",
                "n": len(convergence), "top": convergence[: args.top]},
            "F2_single_attestation": {
                "definition": f"surface in exactly 1 of {n_sources} sources — knowledge at risk",
                "n": len(single), "top": single[: args.top]},
            "F3_orphan_procedures": {
                "definition": "a 炮制 step attested in exactly 1 source while the drug has >=2",
                "n": len(orphans), "top": orphans[: args.top]},
            "F4_corroborated_core": {
                "definition": "surface attested in >=20 independent sources — the stable core",
                "n": len(corroborated), "top": corroborated[: args.top]},
        },
    }
    (ROOT / args.out_json).write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")

    L = ["# Discoveries extracted from the corpus", "", payload["generated_at"], "",
         f"**Input:** {n_chunks:,} corpus chunks containing a drug mention, across **{n_sources} independent "
         f"sources**; {len(src):,} of {len(surfaces):,} lexicon drug surfaces attested.", "",
         "These are properties of the corpus — how many independent traditions and sources support a",
         "drug, which procedures were transmitted once — not sentences generated about a plant.", ""]

    L += [f"## F1 — Cross-tradition convergence ({len(convergence)} surfaces)", "",
          "A drug independently attested in two or more traditions is corroborated by quasi-independent",
          "observations. This is the strongest prior the record can give, and it is why the cross-",
          "tradition join matters: here it is computed from the text, not from the broken structured join.", "",
          "| Surface | Drug | Traditions | Sources |", "|---|---|---|---|"]
    for r in convergence[:15]:
        L.append(f"| {r['surface']} | *{r['drug']}* | {', '.join(r['traditions'])} | {r['n_sources']} |")

    L += ["", f"## F2 — Single-attestation knowledge ({len(single)} surfaces)", "",
          f"**{len(single)}** of {len(src):,} attested surfaces appear in exactly **one** of {n_sources} "
          "sources. Their entire textual record is one document; if it is lost or mis-scanned, the "
          "knowledge is gone. This is a preservation priority computed from the corpus rather than",
          "argued from principle.", "",
          "| Surface | Drug | Sole source |", "|---|---|---|"]
    for r in single[:15]:
        L.append(f"| {r['surface']} | *{r['drug']}* | {r['sources'][0] if r['sources'] else ''} |")

    L += ["", f"## F3 — Orphan procedures ({len(orphans)} drug×process pairs)", "",
          "A 炮制 step attested for a drug in **exactly one text**, while the drug itself is documented",
          "with several procedures. Either a local innovation that never entered the pharmacopoeia, or a",
          "transmission failure. Both are testable: process it, and see whether the chemistry moves.", "",
          "| Drug | Process | Modern operation | Sole source |", "|---|---|---|---|"]
    for o in orphans[:20]:
        L.append(f"| {o['drug']} | {o['process']} | {(o['modern'] or '')[:44]} | {o['source']} |")

    L += ["", f"## F4 — The corroborated core ({len(corroborated)} surfaces in ≥20 sources)", "",
          "Where the whole tradition agrees. These are the safest starting points for a screening",
          "campaign, and the best calibration set for any extraction method: if a method cannot recover",
          "the corroborated core, it is not extracting the tradition.", "",
          "| Surface | Drug | Sources | Traditions |", "|---|---|---|---|"]
    for r in corroborated[:15]:
        L.append(f"| {r['surface']} | *{r['drug']}* | {r['n_sources']} | {', '.join(r['traditions'])} |")

    L += ["", "## What this method gives that a claim generator does not", "",
          "An earlier pass generated grammatically perfect claims with real citations and false content —",
          "including *\"去節 of Aconitum enriches alkaloid via standardising ephedrine\"*, a sentence about",
          "the wrong plant. These four findings cannot be templated: they are counts over 106 sources.",
          "Each is checkable in one lookup, and each is decision-relevant — screening, preservation,",
          "method recovery, and calibration respectively.", ""]
    (ROOT / args.out_md).write_text("\n".join(L), encoding="utf-8")

    print(f"F1 convergence (>=2 traditions): {len(convergence)}")
    print(f"F2 single-source surfaces:       {len(single)}")
    print(f"F3 orphan procedures:            {len(orphans)}")
    print(f"F4 corroborated (>=20 sources):  {len(corroborated)}")
    print(f"wrote {args.out_json} and {args.out_md}")
    for r in convergence[:5]:
        print(f"  conv {r['surface']:<6} *{r['drug']:<30}* {'/'.join(r['traditions']):<28} {r['n_sources']} src")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
