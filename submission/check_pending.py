#!/usr/bin/env python3
"""
Ship gate: fail if a `[[PENDING: …]]` placeholder survives into a shipped artefact.

Placeholders are how this project stays honest while numbers are still arriving from the pipeline. But a
placeholder in a Devpost page is worse than a missing number, because it looks like a measurement. So the rule
is mechanical rather than remembered: **nothing ships with a `[[PENDING` in it.**

    python submission/check_pending.py            # exit 0 = clean, exit 1 = placeholders remain
    python submission/check_pending.py --list     # also print every occurrence with file:line

Deliberately scanned: the artefacts a judge or reviewer reads. Deliberately NOT scanned: this file, the
numbers ledger (which is *supposed* to list what is pending), and git internals.
"""

from __future__ import annotations

import argparse
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# Folders whose contents are shipped to a judge.
SCAN_DIRS = ["docs", "submission", "app", "assets"]

# Individual files at the repository root that may be shipped.
SCAN_FILES = ["README.md"]

# Files that are allowed to mention the placeholder token.
ALLOW = {
    os.path.join("docs", "NUMBERS.md"),          # the ledger of what is pending, by design
    os.path.join("submission", "check_pending.py"),  # this file
    os.path.join("submission", "build_slides_json.py"),  # mentions it in a validation message
}

TOKEN = re.compile(r"\[\[PENDING:\s*([^\]]+?)\]\]")
TEXT_EXT = {".md", ".py", ".json", ".html", ".css", ".js", ".svg", ".txt", ".yaml", ".yml"}


def iter_files():
    for d in SCAN_DIRS:
        base = os.path.join(ROOT, d)
        if not os.path.isdir(base):
            continue
        for dirpath, dirnames, filenames in os.walk(base):
            dirnames[:] = [x for x in dirnames if x not in {".git", "__pycache__", "node_modules"}]
            for fn in filenames:
                if os.path.splitext(fn)[1].lower() not in TEXT_EXT:
                    continue
                full = os.path.join(dirpath, fn)
                yield os.path.relpath(full, ROOT)
    for fn in SCAN_FILES:
        full = os.path.join(ROOT, fn)
        if os.path.isfile(full):
            yield fn


def main(argv=None):
    ap = argparse.ArgumentParser(description="Fail if a [[PENDING: …]] placeholder is still present")
    ap.add_argument("--list", action="store_true", help="print every occurrence with file:line")
    ap.add_argument("--quiet", action="store_true", help="only print the summary")
    args = ap.parse_args(argv)

    hits = []
    scanned = 0
    for rel in sorted(iter_files()):
        if rel in ALLOW:
            continue
        try:
            with open(os.path.join(ROOT, rel), "r", encoding="utf-8", errors="replace") as f:
                lines = f.readlines()
        except OSError:
            continue
        scanned += 1
        for i, line in enumerate(lines, 1):
            for m in TOKEN.finditer(line):
                hits.append((rel, i, m.group(1).strip()))

    if not hits:
        if not args.quiet:
            print(f"✓ clean — no [[PENDING: …]] placeholders in {scanned} shipped files")
        return 0

    print(f"✗ {len(hits)} [[PENDING: …]] placeholder(s) remain across {scanned} scanned files", file=sys.stderr)
    if args.list:
        print(file=sys.stderr)
        for rel, line, name in hits:
            print(f"  {rel}:{line}  →  {name}", file=sys.stderr)
    by_file: dict = {}
    for rel, _, name in hits:
        by_file.setdefault(rel, []).append(name)
    print(file=sys.stderr)
    for rel, names in sorted(by_file.items()):
        print(f"  {rel}  ({len(names)})", file=sys.stderr)
        for n in dict.fromkeys(names):
            print(f"      · {n}", file=sys.stderr)
    print(f"\nRun with --list for file:line. The ledger is docs/NUMBERS.md.", file=sys.stderr)
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
