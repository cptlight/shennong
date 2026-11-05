"""Assemble ``corpus/registry/sources.yaml`` from the per-source ``meta.json`` sidecars.

The registry is the provenance ledger (PROJECT_BRIEF §10.1). Every ``chars`` and ``sha256``
in it is read off an actual file on disk -- nothing here is estimated or hand-typed.

    python -m data.build_registry
"""

from __future__ import annotations

import json
import sys

import yaml

from . import _net, manifest

OUT = _net.REGISTRY / "sources.yaml"

# registry key order (stable diffs, matches the contract)
ORDER = ["id", "title", "title_en", "author", "year", "tradition", "lang", "tier",
         "url", "licence", "licence_evidence", "licence_note", "chars", "chars_raw",
         "sha256", "status"]


def collect() -> list[dict]:
    rows = []
    raw = _net.RAW
    for d in sorted(raw.iterdir()) if raw.exists() else []:
        meta_path = d / "meta.json"
        if not meta_path.exists():
            continue
        meta = json.loads(meta_path.read_text(encoding="utf-8"))
        sid = d.name
        # a source only enters the ledger once it has been cleaned and measured; a half-
        # downloaded work must never appear with chars=0 and status=ok.
        if "clean_stats" not in meta:
            continue
        clean_path = _net.PROCESSED / "text" / f"{sid}.txt"
        raw_file = meta.get("raw_file", "text.raw")
        raw_path = d / raw_file
        cs = (meta.get("clean_stats") or {})

        status = meta.get("status", "ok")
        note = None
        if status == "ok" and cs and not cs.get("clean", False):
            status = "excluded"
            note = ("excluded from training: failed script/quality gate at cleaning "
                    f"(script_ok={cs.get('script_ok')}, "
                    f"replacement_ratio={cs.get('replacement_ratio')})")

        row = {
            "id": sid,
            "title": meta.get("title", ""),
            "title_en": meta.get("title_en", ""),
            "author": meta.get("author", ""),
            "year": meta.get("year"),
            "tradition": meta.get("tradition", ""),
            "lang": meta.get("lang", ""),
            "tier": meta.get("tier"),
            "url": meta.get("url", ""),
            "licence": meta.get("licence", ""),
            "licence_evidence": meta.get("licence_evidence", ""),
            "licence_note": meta.get("licence_note", ""),
            "chars": len(clean_path.read_text(encoding="utf-8")) if clean_path.exists() else 0,
            "chars_raw": meta.get("raw_chars") or meta.get("raw_bytes", 0),
            "sha256": meta.get("raw_sha256") or (_net.sha256_file(raw_path) if raw_path.exists() else ""),
            "status": status,
        }
        if note:
            row["status_note"] = note
        rows.append(row)

    # reference-only entries (never trained on) come from the manifest
    for ref in manifest.REFERENCE_ONLY:
        r = {k: ref.get(k) for k in ORDER if k in ref}
        r["title"] = ref.get("title", "")
        r.setdefault("title_en", "")
        r.setdefault("author", "")
        r.setdefault("year", None)
        r.setdefault("chars", 0)
        r.setdefault("sha256", "")
        r["status_note"] = ref.get("reason", "")
        rows.append(r)

    rows.sort(key=lambda r: (r.get("tier") if isinstance(r.get("tier"), int) else 99,
                             r.get("id", "")))
    return rows


def main(argv=None) -> int:
    rows = collect()
    if not rows:
        raise SystemExit("no sources found in corpus/raw -- fetch something first")
    ordered = [{k: r[k] for k in ORDER if k in r} |
               {k: v for k, v in r.items() if k not in ORDER} for r in rows]
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(yaml.safe_dump(ordered, allow_unicode=True, sort_keys=False,
                                  width=1000), encoding="utf-8")

    ok = sum(1 for r in rows if r["status"] == "ok")
    by_status: dict[str, int] = {}
    by_tradition: dict[str, int] = {}
    for r in rows:
        by_status[r["status"]] = by_status.get(r["status"], 0) + 1
        by_tradition[r["tradition"]] = by_tradition.get(r["tradition"], 0) + 1
    print(f"wrote {OUT} -- {len(rows)} sources, {ok} ok")
    print("status:", dict(sorted(by_status.items())))
    print("tradition:", dict(sorted(by_tradition.items(), key=lambda x: -x[1])))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
