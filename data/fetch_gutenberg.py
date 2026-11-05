"""Fetch Project Gutenberg texts into corpus/raw/.

We use the *cache* endpoint (https://www.gutenberg.org/cache/epub/<id>/pg<id>.txt) because it
is a single stable plaintext file per ebook, and fall back to the /files/ layout for the few
ebooks not present in the cache. Gutenberg politely asks bulk users to mirror rather than
hammer; we fetch a few dozen books once, rate limited, with an honest User-Agent.

    python -m data.fetch_gutenberg
    python -m data.fetch_gutenberg --only pg_origin_of_species
"""

from __future__ import annotations

import argparse
import json
import sys

from . import _net, manifest

CACHE_URL = "https://www.gutenberg.org/cache/epub/{gid}/pg{gid}.txt"
FILES_URL = "https://www.gutenberg.org/files/{gid}/{gid}-0.txt"


def fetch_one(entry: dict, dest) -> dict:
    gid = entry["gid"]
    dest.mkdir(parents=True, exist_ok=True)
    raw = dest / "text.raw"
    if not raw.exists() or raw.stat().st_size < 2000:
        urls = [CACHE_URL.format(gid=gid), FILES_URL.format(gid=gid)]
        last = None
        for u in urls:
            try:
                _net.download(u, raw, min_bytes=2000)
                break
            except Exception as e:
                last = e
        else:
            raise RuntimeError(f"could not download gutenberg {gid}: {last}")
    meta = dict(entry)
    meta.pop("gid", None)
    meta.update({
        "fetcher": "gutenberg",
        "url": f"https://www.gutenberg.org/ebooks/{gid}",
        "raw_file": "text.raw",
        "raw_bytes": raw.stat().st_size,
        "raw_sha256": _net.sha256_file(raw),
    })
    (dest / "meta.json").write_text(json.dumps(meta, indent=1, ensure_ascii=False),
                                    encoding="utf-8")
    return meta


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--only", action="append", default=None)
    ap.add_argument("--force", action="store_true")
    args = ap.parse_args(argv)

    entries = [e for e in manifest.ALL_SOURCES if e["kind"] == "gutenberg"]
    if args.only:
        entries = [e for e in entries if e["id"] in set(args.only)]

    done = skipped = failed = 0
    for e in entries:
        dest = _net.RAW / e["id"]
        if not args.force and (dest / "meta.json").exists() and (dest / "text.raw").exists():
            print(f"[skip] {e['id']}")
            skipped += 1
            continue
        try:
            m = fetch_one(e, dest)
            print(f"[ok]   {e['id']:<42} {m['raw_bytes']:>9,} bytes")
            done += 1
        except Exception as ex:
            print(f"[FAIL] {e['id']}: {ex!r}", file=sys.stderr)
            failed += 1
    print(f"\nfetched={done} skipped={skipped} failed={failed}")
    return 0 if failed == 0 else 2


if __name__ == "__main__":
    raise SystemExit(main())
