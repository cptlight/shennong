"""Fetch Internet Archive items into corpus/raw/.

For each pinned identifier we read ``https://archive.org/metadata/<id>``, pick the best plain
text file (``*_djvu.txt`` produced by IA's OCR; occasionally ``*_text.txt``) and download it.
The untouched OCR is kept in ``corpus/raw/<id>/text.raw`` -- the cleaner in ``data/clean.py``
turns it into training text.

    python -m data.fetch_archive
    python -m data.fetch_archive --only ia_bhishagratna_sushruta
"""

from __future__ import annotations

import argparse
import json
import sys

from . import _net, manifest

DOWNLOAD = "https://archive.org/download/{ident}/{name}"
METADATA = "https://archive.org/metadata/{ident}"


def pick_text_file(ident: str) -> tuple[str, int]:
    """Choose the plaintext derivative and return (name, size_in_metadata)."""
    meta = _net.get_json(METADATA.format(ident=ident), timeout=90)
    files = meta.get("files", [])
    cands = []
    for f in files:
        name = f.get("name", "")
        if not name.endswith(".txt"):
            continue
        size = int(f.get("size") or 0)
        # prefer the djvu OCR derivative; then any *_text.txt
        rank = 0 if name.endswith("_djvu.txt") else (1 if name.endswith("_text.txt") else 2)
        cands.append((rank, -size, name, size))
    if not cands:
        raise RuntimeError(f"{ident}: no plaintext derivative in metadata")
    cands.sort()
    _, _, name, size = cands[0]
    return name, size


def fetch_one(entry: dict, dest) -> dict:
    ident = entry["identifier"]
    dest.mkdir(parents=True, exist_ok=True)
    raw = dest / "text.raw"
    name, declared = pick_text_file(ident)
    if not raw.exists() or raw.stat().st_size < 5000:
        url = DOWNLOAD.format(ident=ident, name=name)
        _net.download(url, raw, timeout=600, min_bytes=5000)
    meta = dict(entry)
    meta.pop("identifier", None)
    meta.update({
        "fetcher": "archive",
        "url": f"https://archive.org/details/{ident}",
        "ia_identifier": ident,
        "ia_file": name,
        "ia_declared_bytes": declared,
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

    entries = [e for e in manifest.ALL_SOURCES if e["kind"] == "archive"]
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
            print(f"[ok]   {e['id']:<44} {m['raw_bytes']:>10,} bytes  ({m['ia_file']})")
            done += 1
        except Exception as ex:
            print(f"[FAIL] {e['id']}: {ex!r}", file=sys.stderr)
            failed += 1
    print(f"\nfetched={done} skipped={skipped} failed={failed}")
    return 0 if failed == 0 else 2


if __name__ == "__main__":
    raise SystemExit(main())
