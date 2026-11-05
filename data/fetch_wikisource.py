"""Fetch the classical Chinese and Sanskrit canon from Wikisource into corpus/raw/.

Usage
-----
    python -m data.fetch_wikisource              # everything not yet on disk
    python -m data.fetch_wikisource --only ws_zh_shennong_bencaojing
    python -m data.fetch_wikisource --lang zh    # one language only
    python -m data.fetch_wikisource --force      # refetch even if present

Idempotent/resumable: a source is skipped when ``corpus/raw/<id>/meta.json`` and a non-empty
``text.raw`` already exist. API responses are cached under ``data/.cache`` so an interrupted
run resumes cheaply.
"""

from __future__ import annotations

import argparse
import json
import sys

from . import _net, manifest
from .wikisource import harvest_to_meta


def _already_done(dest) -> bool:
    meta = dest / "meta.json"
    raw = dest / "text.raw"
    return meta.exists() and raw.exists() and raw.stat().st_size > 2000


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--only", action="append", default=None)
    ap.add_argument("--lang", choices=["zh", "sa"], default=None)
    ap.add_argument("--force", action="store_true")
    args = ap.parse_args(argv)

    entries = [e for e in manifest.ALL_SOURCES if e["kind"] == "wikisource"]
    if args.only:
        wanted = set(args.only)
        entries = [e for e in entries if e["id"] in wanted]
    if args.lang:
        prefix = "ws_" + args.lang
        entries = [e for e in entries if e["id"].startswith(prefix)]

    if not entries:
        print("no matching wikisource entries", file=sys.stderr)
        return 1

    done = skipped = failed = 0
    for e in entries:
        dest = _net.RAW / e["id"]
        if not args.force and _already_done(dest):
            print(f"[skip] {e['id']}")
            skipped += 1
            continue
        try:
            harvest_to_meta(e, dest)
            done += 1
        except Exception as ex:  # keep going; one bad source must not stop the run
            print(f"[FAIL] {e['id']}: {ex!r}", file=sys.stderr)
            failed += 1
    print(f"\nfetched={done} skipped={skipped} failed={failed}")
    return 0 if failed == 0 else 2


if __name__ == "__main__":
    raise SystemExit(main())
