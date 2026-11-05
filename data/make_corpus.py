"""Single entry point for the SHENNONG corpus pipeline.

    python -m data.make_corpus              # full rebuild from scratch (network)
    python -m data.make_corpus --offline    # rebuild from existing corpus/raw (no network)
    python -m data.make_corpus --stage fetch
    python -m data.make_corpus --stage build
    python -m data.make_corpus --stage structured

Stages
------
fetch       download raw text into corpus/raw/<id>/          (network, idempotent)
clean       raw -> corpus/processed/text/<id>.txt             (local)
build       cleaned -> corpus.jsonl + stats.json              (local)
registry    -> corpus/registry/sources.yaml                   (local)
docs        -> corpus/DATA_CARD.md + licence table            (local)
structured  -> corpus/processed/structured/*.csv              (network: Wikidata/PubChem/GBIF)
lexicon     -> corpus/processed/lexicon_drugs.json            (network: Wikidata)
report      -> corpus/registry/join_report.json               (local)

The stages are ordered and idempotent; every fetcher caches to `data/.cache/` and every
writer is a pure function of its inputs, so a crashed run resumes rather than restarting.
"""

from __future__ import annotations

import argparse
import subprocess
import sys
import time

STAGES = ["fetch", "clean", "build", "registry", "docs", "structured", "lexicon", "report"]

FETCH = [
    ["-m", "data.fetch_wikisource", "--lang", "zh"],
    ["-m", "data.fetch_wikisource", "--lang", "sa"],
    ["-m", "data.fetch_gutenberg"],
    ["-m", "data.fetch_archive"],
]
LOCAL = {
    "clean": [["-m", "data.clean"]],
    "build": [["-m", "data.build_corpus"]],
    "registry": [["-m", "data.build_registry"]],
    "docs": [["-m", "data.build_docs"]],
    "structured": [["-m", "data.build_structured"]],
    "lexicon": [["-m", "data.build_lexicon"]],
    "report": [["-m", "data.build_join_report"]],
}
# order within the structured stage: the lexicon must exist before the CSVs can join
STRUCTURED_ORDER = ["lexicon", "structured", "report", "docs"]


def run(args: list[str]) -> int:
    cmd = [sys.executable, *args]
    print(f"\n$ {' '.join(cmd[1:])}", flush=True)
    t0 = time.time()
    rc = subprocess.call(cmd)
    print(f"  -> exit {rc} ({time.time() - t0:.0f}s)", flush=True)
    return rc


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--stage", action="append", choices=STAGES, default=None)
    ap.add_argument("--offline", action="store_true",
                    help="skip network stages (fetch, structured, lexicon)")
    args = ap.parse_args(argv)

    selected = args.stage or STAGES
    if args.offline:
        selected = [s for s in selected if s not in ("fetch", "structured", "lexicon")]

    failures = []
    for stage in STAGES:
        if stage not in selected:
            continue
        print(f"\n{'=' * 70}\nSTAGE: {stage}\n{'=' * 70}", flush=True)
        cmds = FETCH if stage == "fetch" else LOCAL[stage]
        for c in cmds:
            rc = run(c)
            if rc != 0:
                failures.append((stage, " ".join(c), rc))
                print(f"  ! stage {stage} failed; continuing so partial artefacts exist",
                      file=sys.stderr)

    print(f"\n{'=' * 70}")
    if failures:
        print("FAILURES:")
        for stage, cmd, rc in failures:
            print(f"  {stage}: {cmd} -> {rc}")
        return 1
    print("all stages OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
