#!/usr/bin/env python3
"""
SHENNONG Workbench — a local-first research cockpit for the SHENNONG discovery engine.

    python app/serve.py            # then open the printed URL

Standard library only. No build step, no CDN, no network. Works offline on a CPU-only machine.

WHAT IT READS (each artefact independently, with graceful fallback)
-------------------------------------------------------------------
  eval/report.json                     -> 使 Shǐ evaluation panel + negative controls   (brief §10.7)
  training/runs/*/metrics.json         -> loss curve on the Methodology panel            (brief §10.6)
  corpus/registry/sources.yaml         -> 采 Cǎi provenance panel                        (brief §10.1)
  app/data/hypotheses.json             -> `python -m shennong.cli shi --out ...`
  app/data/kg.json                     -> `python -m shennong.cli pei --out-kg ...`
  app/data/passages.json               -> `python -m shennong.cli cai --out-passages ...`

If an artefact is absent, the panel that needs it renders from the bundled DEMO FIXTURE in
app/data/ (built by app/data/make_fixtures.py) and carries a visible DEMO FIXTURE badge.
Every response states which files were real and which were fixture — the UI never mixes them
silently. `--strict` refuses to start on fixture data, which is what we run for the final video.

If `shennong.rag.answer()` is importable, the Ask panel calls it. Otherwise it falls back to an
honest local BM25 extractive retriever over the passage index, and *says so in the UI*.
"""

from __future__ import annotations

import argparse
import glob
import html
import json
import math
import os
import re
import socket
import sys
import threading
import unicodedata
import webbrowser
from datetime import datetime, timezone
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qs, urlparse

APP_DIR = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(APP_DIR)
# ROOT must be importable at module load, not just inside the ask() helper: /api/query imports the
# shennong package at request time and was failing with ModuleNotFoundError.
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)
STATIC_DIR = os.path.join(APP_DIR, "static")
DATA_DIR = os.path.join(APP_DIR, "data")
VERSION = "0.2.0"

NAME = "SHENNONG"
NAME_CN = "神农"
TAGLINE = ("Shennong tasted a hundred herbs. We are teaching a 400 MB model to do it again — "
           "and to tell us what he hid between the lines.")
PIPELINE = ["采 Cǎi", "制 Zhì", "配 Pèi", "使 Shǐ"]

# ---------------------------------------------------------------------------------------------
# Diagnostics log — printed once at startup so a judge can see exactly what is real
# ---------------------------------------------------------------------------------------------
REPORT: list = []


def note(msg: str) -> None:
    REPORT.append(msg)


# ---------------------------------------------------------------------------------------------
# Tiny tolerant YAML reader for corpus/registry/sources.yaml (brief §10.1).
# We must not depend on PyYAML: the Workbench is stdlib-only. This handles the documented shape
# (a top-level list of flat mappings with scalar values) and degrades to None on anything else.
# ---------------------------------------------------------------------------------------------
def _yaml_scalar(raw: str):
    raw = raw.strip()
    if not raw or raw in ("~", "null", "Null", "NULL"):
        return None
    if (raw.startswith('"') and raw.endswith('"')) or (raw.startswith("'") and raw.endswith("'")):
        body = raw[1:-1]
        return body.replace('\\"', '"') if raw.startswith('"') else body.replace("''", "'")
    low = raw.lower()
    if low in ("true", "yes"):
        return True
    if low in ("false", "no"):
        return False
    try:
        return int(raw)
    except ValueError:
        pass
    try:
        return float(raw)
    except ValueError:
        pass
    if raw.startswith("[") and raw.endswith("]"):
        inner = raw[1:-1].strip()
        return [_yaml_scalar(p) for p in inner.split(",")] if inner else []
    return raw


def parse_sources_yaml(path: str):
    try:
        with open(path, "r", encoding="utf-8") as f:
            lines = f.read().splitlines()
    except OSError:
        return None
    out, cur = [], None
    for line in lines:
        if not line.strip() or line.lstrip().startswith("#"):
            continue
        stripped = line.strip()
        if stripped.startswith("- "):
            cur = {}
            out.append(cur)
            stripped = stripped[2:].strip()
            if not stripped:
                continue
        if cur is None:
            continue
        if ":" not in stripped:
            continue
        key, _, val = stripped.partition(":")
        key, val = key.strip(), val.strip()
        # strip trailing comments that are not inside quotes
        if val and not val.startswith(('"', "'")) and " #" in val:
            val = val.split(" #", 1)[0].strip()
        cur[key] = _yaml_scalar(val)
    return out or None


def normalise_sources(rows):
    """Map whatever the registry uses onto the panel's field names."""
    out = []
    for r in rows or []:
        if not isinstance(r, dict):
            continue
        sid = r.get("id") or r.get("source_id") or ""
        if not sid:
            continue
        out.append(dict(
            id=sid,
            title=r.get("title") or sid,
            title_en=r.get("title_en") or "",
            author=r.get("author") or "",
            year=r.get("year"),
            tradition=r.get("tradition") or "unclassified",
            lang=r.get("lang") or "en",
            tier=r.get("tier") if isinstance(r.get("tier"), int) else 0,
            licence=r.get("licence") or "UNVERIFIED",
            url=r.get("url") or "",
            chars=r.get("chars") if isinstance(r.get("chars"), int) else None,
            status=r.get("status") or "ok",
        ))
    return out


# ---------------------------------------------------------------------------------------------
# Artefact loading
# ---------------------------------------------------------------------------------------------
def _read_json(path: str):
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except (OSError, json.JSONDecodeError):
        return None


def _mtime(path: str) -> float:
    try:
        return os.path.getmtime(path)
    except OSError:
        return 0.0


def load_hypotheses():
    real = os.path.join(DATA_DIR, "hypotheses.json")
    d = _read_json(real)
    if isinstance(d, dict) and isinstance(d.get("hypotheses"), list) and d["hypotheses"]:
        return _finish(d, "app/data/hypotheses.json", bool(d.get("fixture")))
    fx = _read_json(os.path.join(DATA_DIR, "hypotheses.json"))
    if isinstance(fx, dict):
        return _finish(fx, "app/data/hypotheses.json", True)
    return dict(hypotheses=[], fixture=True, source="(missing)", counts={})


def _finish(d, source, fixture):
    hyps = []
    for i, h in enumerate(d.get("hypotheses", [])):
        if not isinstance(h, dict):
            continue
        chain = h.get("chain") or {}
        scores = h.get("scores") or {}
        for k in ("novelty", "plausibility", "testability", "evidence", "composite"):
            v = scores.get(k)
            scores[k] = float(v) if isinstance(v, (int, float)) else 0.0
        hyps.append(dict(
            id=h.get("id") or f"H-{i + 1:02d}",
            rank=h.get("rank") or i + 1,
            title=h.get("title") or "(untitled hypothesis)",
            discovery_class=h.get("discovery_class") or "unclassified",
            discovery_class_label=h.get("discovery_class_label") or h.get("discovery_class") or "unclassified",
            chain={k: chain.get(k, "") for k in ("plant", "preparation", "chemotype", "target", "indication")},
            scores=scores,
            provenance=h.get("provenance") or [],
            falsification_plan=h.get("falsification_plan") or "",
            uncertainty=h.get("uncertainty") or "",
            safety=h.get("safety") or {"flags": [], "severity": "none"},
            dossier=h.get("dossier") or {},
            is_control=bool(h.get("is_control")),
        ))
    hyps.sort(key=lambda x: (x["rank"], -x["scores"]["composite"]))
    by_class: dict = {}
    for h in hyps:
        by_class[h["discovery_class"]] = by_class.get(h["discovery_class"], 0) + 1
    return dict(hypotheses=hyps, fixture=fixture, source=source,
                generated_at=d.get("generated_at"), note=d.get("note"),
                pipeline=d.get("pipeline") or " → ".join(PIPELINE),
                corpus=d.get("corpus") or {}, by_class=by_class,
                counts=dict(total=len(hyps), classes=len(by_class),
                            discovered=len([h for h in hyps if not h["is_control"]]),
                            controls=len([h for h in hyps if h["is_control"]])))


def load_kg():
    d = _read_json(os.path.join(DATA_DIR, "kg.json"))
    if not isinstance(d, dict) or not isinstance(d.get("nodes"), list):
        return dict(nodes=[], edges=[], layout={}, fixture=True, source="(missing)")
    nodes = [n for n in d["nodes"] if isinstance(n, dict) and n.get("id")]
    edges = [e for e in d.get("edges", []) if isinstance(e, dict) and e.get("source") and e.get("target")]
    layout = d.get("layout") if isinstance(d.get("layout"), dict) else {}
    if not layout:
        layout = compute_layout(nodes, edges)
    return dict(nodes=nodes, edges=edges, layout=layout, fixture=bool(d.get("fixture")),
                generated_at=d.get("generated_at"), source="app/data/kg.json",
                types=sorted({n.get("type", "concept") for n in nodes}))


def compute_layout(nodes, edges, w=1240.0, h=840.0, iters=260):
    """Deterministic spring layout for KG exports that omit `layout` (discovery-engine's contract)."""
    import random

    ids = [n["id"] for n in nodes]
    if not ids:
        return {}
    rnd = random.Random(11)
    n = len(ids)
    pos = {}
    for i, nid in enumerate(ids):
        t = 2 * math.pi * i / n
        pos[nid] = [w / 2 + (w / 3) * math.cos(t) * (0.7 + 0.6 * rnd.random()),
                    h / 2 + (h / 3) * math.sin(t) * (0.7 + 0.6 * rnd.random())]
    adj = [(e["source"], e["target"]) for e in edges if e["source"] in pos and e["target"] in pos]
    if n > 160:
        iters = 120
    k = math.sqrt(w * h / n)
    for it in range(iters):
        disp = {i: [0.0, 0.0] for i in ids}
        for i in range(n):
            for j in range(i + 1, n):
                a, b = ids[i], ids[j]
                dx, dy = pos[a][0] - pos[b][0], pos[a][1] - pos[b][1]
                d2 = dx * dx + dy * dy
                if d2 < 1e-6:
                    dx, dy, d2 = rnd.random() - 0.5, rnd.random() - 0.5, 1e-6
                d = math.sqrt(d2)
                f = k * k / d
                ux, uy = dx / d, dy / d
                disp[a][0] += ux * f
                disp[a][1] += uy * f
                disp[b][0] -= ux * f
                disp[b][1] -= uy * f
        for a, b in adj:
            dx, dy = pos[a][0] - pos[b][0], pos[a][1] - pos[b][1]
            d = max(math.sqrt(dx * dx + dy * dy), 1e-6)
            f = d * d / k
            ux, uy = dx / d, dy / d
            disp[a][0] -= ux * f
            disp[a][1] -= uy * f
            disp[b][0] += ux * f
            disp[b][1] += uy * f
        temp = (k * 1.8) * (1 - it / iters) ** 1.6
        for nid in ids:
            dx, dy = disp[nid]
            d = max(math.sqrt(dx * dx + dy * dy), 1e-6)
            step = min(d, temp)
            pos[nid][0] += dx / d * step
            pos[nid][1] += dy / d * step
            pos[nid][0] += (w / 2 - pos[nid][0]) * 0.005
            pos[nid][1] += (h / 2 - pos[nid][1]) * 0.005
    return {nid: [round(min(max(pos[nid][0], 40), w - 40), 1),
                  round(min(max(pos[nid][1], 40), h - 40), 1)] for nid in ids}


def load_passages():
    d = _read_json(os.path.join(DATA_DIR, "passages.json"))
    if isinstance(d, dict) and isinstance(d.get("passages"), list) and d["passages"]:
        return dict(passages=[p for p in d["passages"] if isinstance(p, dict) and p.get("text")],
                    fixture=bool(d.get("fixture")), source="app/data/passages.json")
    return dict(passages=[], fixture=True, source="(missing)")


def load_emitted_stats():
    """`corpus/processed/stats.json` is the corpus builder's own output for the text it actually emitted.

    It is authoritative for *training text*: the registry counts what was fetched, this counts what was
    written to corpus.jsonl after cleaning and dedupe. The two legitimately differ, so the panel shows the
    emitted figure and says which it is showing.
    """
    d = _read_json(os.path.join(ROOT, "corpus", "processed", "stats.json"))
    if not isinstance(d, dict) or not isinstance(d.get("chars_total"), int):
        return None
    return dict(sources=d.get("sources_total"), records=d.get("records"),
                chars=d.get("chars_total"), chars_cjk=d.get("chars_cjk"),
                chars_non_cjk=d.get("chars_non_cjk"), tokens_estimate=d.get("tokens_estimate"),
                dup_dropped=d.get("duplicate_chunks_dropped"),
                corpus_sha256=d.get("corpus_sha256"), corpus_bytes=d.get("corpus_bytes"),
                by_tier=d.get("chars_by_tier") or {}, by_tradition=d.get("chars_by_tradition") or {},
                by_lang=d.get("chars_by_lang") or {}, generated_at=d.get("generated_at"))


def load_corpus():
    emitted = load_emitted_stats()
    ypath = os.path.join(ROOT, "corpus", "registry", "sources.yaml")
    rows = normalise_sources(parse_sources_yaml(ypath))
    if rows:
        res = _summarise_corpus(rows, "corpus/registry/sources.yaml", False)
    else:
        fx = _read_json(os.path.join(DATA_DIR, "corpus.json"))
        rows = normalise_sources((fx or {}).get("sources"))
        res = (_summarise_corpus(rows, "app/data/corpus.json", True,
                                 built=(fx or {}).get("built"), stages=(fx or {}).get("stages"))
               if rows else _summarise_corpus([], "(missing)", True))
    if emitted:
        res["emitted"] = emitted
        res["stats"]["chars"] = emitted["chars"]          # authoritative for emitted text
    return res


ERA_BUCKETS = [
    ("pre-500 CE", -5000, 500),
    ("500–1000", 500, 1000),
    ("1000–1500", 1000, 1500),
    ("1500–1700", 1500, 1700),
    ("1700–1900", 1700, 1900),
    ("1900–present", 1900, 3000),
]


def _eras(years):
    """Count sources per era bucket. Derived from the registry's `year`, never hand-written."""
    out = {label: 0 for label, _, _ in ERA_BUCKETS}
    for y in years:
        for label, lo, hi in ERA_BUCKETS:
            if lo <= y < hi:
                out[label] += 1
                break
    return out


def _summarise_corpus(rows, source, fixture, built=None, stages=None):
    tiers: dict = {}
    langs: dict = {}
    traditions: dict = {}
    licences: dict = {}
    years = []
    kept = excluded = 0
    chars = 0
    for r in rows:
        if r["status"] == "ok":
            kept += 1
            tiers[str(r["tier"])] = tiers.get(str(r["tier"]), 0) + 1
            langs[r["lang"]] = langs.get(r["lang"], 0) + 1
            traditions[r["tradition"]] = traditions.get(r["tradition"], 0) + 1
            licences[r["licence"]] = licences.get(r["licence"], 0) + 1
            if isinstance(r["year"], int):
                years.append(r["year"])
            if isinstance(r["chars"], int):
                chars += r["chars"]
        else:
            excluded += 1
    return dict(sources=rows, fixture=fixture, source=source,
                built=built or dict(fetched=len(rows), kept=kept, excluded=excluded, chars=chars or None),
                stages=stages or [],
                stats=dict(fetched=len(rows), kept=kept, excluded=excluded, chars=chars or None,
                           tiers=tiers, langs=langs, traditions=traditions, licences=licences,
                           eras=_eras(years),
                           year_min=min(years) if years else None, year_max=max(years) if years else None))


# ---------------------------------------------------------------------------------------------
# Partial Traditional -> Simplified fold, used ONLY for provenance-integrity comparison.
#
# Why this exists: the drug lexicon normalises to Simplified (大黄) while the classical corpus is
# Traditional (大黃). A naive `drug in quote` test therefore reports a false provenance failure for
# every candidate whose name contains a variant character — and a false alarm is as damaging as a
# missed one, because it teaches reviewers to ignore the warning. The table is deliberately partial
# and documented as such; a miss here yields "unmatched", i.e. it errs toward caution, never toward
# falsely certifying an attribution.
# ---------------------------------------------------------------------------------------------
HAN_FOLD = str.maketrans({
    "黃": "黄", "蔘": "参", "參": "参", "藥": "药", "當": "当", "歸": "归", "烏": "乌", "龍": "龙",
    "馬": "马", "門": "门", "貝": "贝", "葉": "叶", "蘇": "苏", "藍": "蓝", "蘆": "芦", "薟": "莶",
    "蓋": "盖", "蔞": "蒌", "蘞": "蔹", "朮": "术", "腎": "肾", "膽": "胆", "腸": "肠", "絡": "络",
    "經": "经", "脈": "脉", "梔": "栀", "翹": "翘", "銀": "银", "連": "连", "陳": "陈", "薑": "姜",
    "荊": "荆", "風": "风", "濕": "湿", "熱": "热", "溫": "温", "涼": "凉", "鹹": "咸", "澀": "涩",
    "耆": "芪", "黨": "党", "頭": "头", "豬": "猪", "朮": "术", "蘗": "蘖", "蘚": "藓", "薑": "姜",
    "龜": "龟", "鼈": "鳖", "鱉": "鳖", "魚": "鱼", "鳥": "鸟", "鳳": "凤", "鶴": "鹤", "雞": "鸡",
    "麥": "麦", "黍": "黍", "鹽": "盐", "鐵": "铁", "銅": "铜", "錫": "锡", "鉛": "铅", "鋅": "锌",
    "礦": "矿", "礦": "矿", "礞": "礞", "鹼": "碱", "鹻": "碱", "釀": "酿", "醱": "酦", "麴": "曲",
    "幾": "几", "後": "后", "發": "发", "為": "为", "與": "与", "無": "无", "醫": "医", "癥": "症",
    "瘕": "瘕", "積": "积", "聚": "聚", "飲": "饮", "蕩": "荡", "滌": "涤", "穀": "谷", "調": "调",
    "氣": "气", "臟": "脏", "腑": "腑", "竅": "窍", "癰": "痈", "腫": "肿", "瘍": "疡", "瘡": "疮",
})


def han_fold(text: str) -> str:
    """Fold Traditional Han to Simplified for comparison only; never for display."""
    return str(text or "").translate(HAN_FOLD)


def provenance_integrity(drug_cjk: str, text: str):
    """Does the quoted span actually mention the drug it is attributed to? Script-variant tolerant."""
    if not text:
        return "absent", "no classical line attached"
    if not drug_cjk:
        return "unknown", "lead drug name not resolvable in script form"
    if drug_cjk in text:
        return "ok", ""
    if han_fold(drug_cjk) in han_fold(text):
        return "ok", f"matched after Traditional/Simplified folding ({drug_cjk})"
    return "unmatched", (f"the quoted span does not mention {drug_cjk}. The attribution is unverified and "
                         "is shown as a warning, not as evidence.")


def load_candidates():
    """artifacts/drug_candidates.json is the real artefact (brief §11.4); the fixture twin lives in app/data.

    Two schemas are accepted: the rich producer schema (`lead`, `candidate_molecule`, `descriptors`,
    `evidence`, `falsification`, `uncertainty`) and the flattened schema documented in the request. Every
    field is read defensively, because this file is produced by another module and may evolve.

    One non-negotiable check happens here: **provenance integrity**. If a classical line is attached to a
    candidate but that line does not mention the drug it is attributed to, we mark it `unmatched` and the UI
    renders a visible warning instead of presenting a misattributed quotation as evidence.
    """
    real = os.path.join(ROOT, "artifacts", "drug_candidates.json")
    d = _read_json(real)
    source = "artifacts/drug_candidates.json"
    # The producer may ship a fixture-flagged artefact at the real path. A file that says it is a fixture is
    # a fixture, whatever directory it lives in — otherwise a panel could claim LIVE while showing test data.
    fixture = True
    if isinstance(d, dict) and isinstance(d.get("candidates"), list) and d["candidates"]:
        fixture = bool(d.get("fixture"))
    else:
        d = _read_json(os.path.join(DATA_DIR, "drug_candidates.json"))
        source, fixture = "app/data/drug_candidates.json", True
    if not (isinstance(d, dict) and isinstance(d.get("candidates"), list)):
        return dict(candidates=[], fixture=True, source="(missing)", counts={})

    cands = []
    for i, c in enumerate(d["candidates"]):
        if not isinstance(c, dict):
            continue
        lead = c.get("classical_lead") or {}
        rich_lead = c.get("lead") or {}
        tcm = ((rich_lead.get("asian_properties") or {}).get("tcm") or {})
        desc = c.get("descriptors") or {}
        nov = c.get("novelty") or {}
        unc = c.get("uncertainty") or {}
        fal = c.get("falsification") or {}

        drug_cjk = tcm.get("drug_name") or ""
        drug_display = drug_cjk or lead.get("drug") or rich_lead.get("drug") or "—"
        formula = c.get("formula") or desc.get("formula")
        mw = c.get("mw") if isinstance(c.get("mw"), (int, float)) else desc.get("mw")
        smiles = c.get("smiles") or desc.get("smiles") or None

        # --- provenance integrity -----------------------------------------------------------
        line = c.get("classical_line") or {}
        text = (line.get("text") or "").strip()
        integrity, integrity_note = provenance_integrity(drug_cjk, text)
        if len(integrity_note) == 0 and line.get("names_drug"):
            integrity_note = f"the producer records this span as naming {line['names_drug']}"

        # --- descriptors / drug-likeness ----------------------------------------------------
        ro5 = dict(
            mw=dict(value=mw, threshold=500, pass_=(mw < 500) if isinstance(mw, (int, float)) else None),
            logp=dict(value=desc.get("logp_estimate"), threshold=5, pass_=None),
            hbd=dict(value=desc.get("hbd"), threshold=5, pass_=None),
            hba=dict(value=desc.get("hba"), threshold=10, pass_=None),
        )
        for k, v in (("logp", desc.get("logp_estimate")), ("hbd", desc.get("hbd")), ("hba", desc.get("hba"))):
            if isinstance(v, (int, float)):
                ro5[k]["pass_"] = v <= ro5[k]["threshold"]
        evaluated = sum(1 for v in ro5.values() if v["pass_"] is not None)
        lipinski = dict(rule_of_five=ro5, evaluated=evaluated, total=4,
                        overall=desc.get("lipinski_pass"), violations=desc.get("lipinski_violations"),
                        veber=desc.get("veber_pass"), tpsa=desc.get("tpsa"),
                        rings=desc.get("rings"), rotatable=desc.get("rotatable_bonds"),
                        sa_score=desc.get("sa_score_heuristic"), flags=desc.get("flags") or {},
                        note=("Descriptors computed by shennong.chem from the resolved structure."
                              if desc else "No structure resolved: molecular weight only, where a formula exists."))

        # --- evidence -> provenance list ----------------------------------------------------
        prov = c.get("provenance") or []
        if not prov:
            for e in (c.get("evidence") or []):
                if not isinstance(e, dict):
                    continue
                prov.append(dict(source_id=e.get("source_id"), title=e.get("title"),
                                 title_en=e.get("title_en") or e.get("title"), author=e.get("author") or "",
                                 year=e.get("year"), tier=e.get("tier"), licence=e.get("licence") or "",
                                 span=e.get("quote") or e.get("span") or "",
                                 span_kind=e.get("span_kind") or "quote",
                                 locator=e.get("locator") or "",
                                 confidence=e.get("confidence")))

        dev = []
        for x in (c.get("development_path") or []):
            if isinstance(x, str):
                dev.append(dict(step=x, kind=""))
            elif isinstance(x, dict):
                dev.append(dict(step=x.get("kind") or x.get("step") or "", kind=x.get("step") if x.get("kind") else ""))

        falsification = c.get("falsification_plan") or ""
        if not falsification and fal:
            bits = []
            if fal.get("experiment"):
                bits.append(str(fal["experiment"]))
            if fal.get("kill_criteria"):
                bits.append(f"Kill criteria: {fal['kill_criteria']}")
            if fal.get("expected_if_true"):
                bits.append(f"If true: {fal['expected_if_true']}")
            falsification = " ".join(bits)

        uncertainty = c.get("uncertainty")
        if not isinstance(uncertainty, str):
            parts = []
            ci = unc.get("composite_ci")
            if isinstance(ci, list) and len(ci) == 2:
                parts.append(f"95% CI on the composite: [{ci[0]:.3f}, {ci[1]:.3f}].")
            for drv in (unc.get("drivers") or [])[:3]:
                parts.append(str(drv).rstrip(".") + ".")
            uncertainty = " ".join(parts)

        cands.append(dict(
            id=c.get("id") or f"C-{i + 1:04d}",
            rank=c.get("rank") or i + 1,
            name=c.get("name") or (c.get("candidate_molecule") or {}).get("name") or "(unnamed)",
            name_cn=c.get("name_cn") or "",
            discovery_class=c.get("discovery_class") or c.get("class") or "unclassified",
            classical_lead=dict(
                drug=drug_display,
                drug_modern=lead.get("drug") or rich_lead.get("drug_modern") or "",
                drug_en=lead.get("drug_en") or rich_lead.get("drug_modern") or "",
                part=lead.get("part") or rich_lead.get("part") or "",
                processing=lead.get("processing") or rich_lead.get("process") or "",
                formula_role=lead.get("formula_role") or rich_lead.get("formula_role") or "",
                indication=rich_lead.get("indication") or "",
                source=lead.get("source") or "",
            ),
            formula=formula, mw=mw, smiles=smiles,
            structure_status=c.get("structure_status") or (c.get("candidate_molecule") or {}).get("structure_status")
                             or ("resolved" if smiles else "pending"),
            structure_note=c.get("structure_note") or (c.get("candidate_molecule") or {}).get("resolution_method") or "",
            theory=dict(nature=theory_get(c, "nature"), flavors=theory_get(c, "flavors") or [],
                        channels=theory_get(c, "channels") or [], direction=theory_get(c, "direction") or "",
                        grade=theory_get(c, "grade") or "", rasa=theory_get(c, "rasa") or [],
                        virya=theory_get(c, "virya") or ""),
            mechanism=c.get("mechanism") or {},
            novelty=dict(score=float(nov.get("score") or (c.get("scores") or {}).get("novelty") or 0.0),
                         basis=nov.get("method") or nov.get("basis") or "",
                         prior_art=nov.get("prior_art") or ""),
            scores=c.get("scores") or {},
            theory_justification=c.get("theory_justification") or c.get("asian_theory_justification") or "",
            development_path=dev,
            residual_risk=c.get("residual_risk") or [],
            safety=c.get("safety") or {"flags": [], "severity": "none"},
            status=c.get("status") or "lead",
            classical_line=dict(
                source=line.get("source") or "", year=line.get("year"),
                locator=line.get("locator") or "", text=text,
                translation=line.get("translation") or "",
                span_kind=line.get("span_kind") or "",
                integrity=integrity, integrity_note=integrity_note),
            druglikeness=lipinski,
            provenance=prov,
            falsification_plan=falsification,
            uncertainty=uncertainty or "",
            raw_class=c.get("class") or "",
        ))

    cands.sort(key=lambda x: (-x["novelty"]["score"], x["rank"]))
    by_status: dict = {}
    for c in cands:
        by_status[c["status"]] = by_status.get(c["status"], 0) + 1
    unmatched = sum(1 for c in cands if c["classical_line"]["integrity"] == "unmatched")
    return dict(candidates=cands, fixture=bool(d.get("fixture")) if fixture else False,
                source=source, generated_at=d.get("generated_at"), note=d.get("note"),
                method=d.get("method"), diagnostics=d.get("diagnostics"),
                counts=dict(total=len(cands),
                            resolved=sum(1 for c in cands if c["smiles"]),
                            by_status=by_status,
                            unmatched_lines=unmatched,
                            mean_novelty=round(sum(c["novelty"]["score"] for c in cands) / max(len(cands), 1), 3)))


def theory_get(c, key):
    """Theory vector may be at `theory` (flat) or `lead.asian_properties.tcm` (rich producer schema)."""
    t = c.get("theory") or {}
    if t.get(key) not in (None, "", []):
        return t.get(key)
    tcm = (((c.get("lead") or {}).get("asian_properties") or {}).get("tcm") or {})
    return tcm.get(key) if tcm.get(key) not in (None, "", []) else t.get(key)


def load_eval():
    real = os.path.join(ROOT, "eval", "report.json")
    d = _read_json(real)
    if isinstance(d, dict) and d.get("benchmarks") is not None:
        # Same rule as the candidate artefact: a report that says it is a fixture is a fixture, whatever
        # path it sits at. Showing preliminary numbers as LIVE would be the exact failure this project
        # claims to design against.
        return dict(report=d, fixture=bool(d.get("fixture")), source="eval/report.json",
                    generated_at=d.get("generated_at"))
    # No measured evaluation yet. Use the clearly-labelled fixture twin so the panel's structure is
    # visible — every value in it is chipped DEMO FIXTURE in the UI, and the banner says so too.
    fx = _read_json(os.path.join(DATA_DIR, "eval_fixture.json"))
    if isinstance(fx, dict) and fx.get("fixture"):
        return dict(report=fx, fixture=True, source="app/data/eval_fixture.json",
                    generated_at=fx.get("generated_at"),
                    awaiting="python -m shennong.cli report --out eval/report.json")
    return dict(report=None, fixture=True, source="(no eval/report.json)", awaiting=None)


_SHA_CACHE: dict = {}


def load_artifacts():
    """Published weight artefacts, verified from disk.

    The sha256 is computed here rather than quoted from a document, so the number on screen is a fact about
    the file in this checkout. That is the whole point of showing it.
    """
    import hashlib
    import struct

    def gguf_header(path):
        """Read tensor_count straight out of the GGUF header (24 bytes). Stdlib only, no gguf dependency."""
        try:
            with open(path, "rb") as f:
                head = f.read(24)
            magic, version, tensor_count, kv_count = struct.unpack("<IIQQ", head)
            if magic != 0x46554747:  # b'GGUF'
                return None
            return dict(version=version, tensors=tensor_count, kv_count=kv_count)
        except (OSError, struct.error):
            return None

    out = []
    for path in sorted(glob.glob(os.path.join(ROOT, "artifacts", "*.gguf"))):
        try:
            st = os.stat(path)
            key = (path, st.st_mtime, st.st_size)
            digest = _SHA_CACHE.get(key)
            if digest is None:
                h = hashlib.sha256()
                with open(path, "rb") as f:
                    for chunk in iter(lambda: f.read(1 << 20), b""):
                        h.update(chunk)
                digest = h.hexdigest()
                _SHA_CACHE.clear()
                _SHA_CACHE[key] = digest
            out.append(dict(name=os.path.basename(path), bytes=st.st_size,
                            mb=round(st.st_size / 1_000_000, 2), mib=round(st.st_size / (1 << 20), 2),
                            sha256=digest, path=os.path.relpath(path, ROOT),
                            header=gguf_header(path)))
        except OSError:
            continue
    return out


def load_metrics():
    paths = sorted(glob.glob(os.path.join(ROOT, "training", "runs", "*", "metrics.json")),
                   key=_mtime, reverse=True)
    for p in paths:
        d = _read_json(p)
        if isinstance(d, dict) and isinstance(d.get("loss_curve"), list) and d["loss_curve"]:
            rel = os.path.relpath(p, ROOT)
            return dict(metrics=d, fixture=False, source=rel)
    return dict(metrics=None, fixture=True, source="(no training/runs/*/metrics.json)",
                awaiting="make train-mini")


# ---------------------------------------------------------------------------------------------
# Ask engine — grounded or refused. Never guesses.
# ---------------------------------------------------------------------------------------------
IAST = {"ā": "a", "ī": "i", "ū": "u", "ṛ": "r", "ṝ": "r", "ḷ": "l", "ṃ": "m", "ṁ": "m",
        "ḥ": "h", "ś": "s", "ṣ": "s", "ṭ": "t", "ḍ": "d", "ṇ": "n", "ñ": "n", "ṅ": "n",
        "Ā": "A", "Ī": "I", "Ū": "U", "Ś": "S", "Ṣ": "S", "Ṭ": "T", "Ḍ": "D", "Ṇ": "N",
        "Ñ": "N", "Ṅ": "N", "Ṃ": "M", "Ḥ": "H"}

STOP = set("""a an the of and or in on for to from with without by is are was were be been being
what which who whom whose when where why how did does do done can could should would may might will
tell explain describe give show me i we you it its this that these those about into over under
there their they them he she his her as at than then so if not no nor but also any some more most
much many such own same other another using used use""".split())

# Personal-use / instruction intent -> medical-safety refusal. Deliberately narrow: research
# questions ("what does the corpus say about X") must pass through.
MED_PATTERNS = [
    r"\bhow (do|can|should) (i|we|you) (take|use|prepare|make|brew|mix|dose|apply)\b",
    r"\b(what|which) (dose|dosage|amount|quantity)\b",
    r"\bhow (much|many) (grams?|g|mg|ml|drops?|pills?|teaspoons?)\b",
    r"\bshould i (take|use|try|stop)\b",
    r"\b(can|may) i (take|use|give)\b",
    r"\bis it safe (to|for)\b",
    r"\bsafe to (take|use|give|consume)\b",
    r"\b(treat|cure|heal|relieve) (my|his|her|our)\b",
    r"\bfor my (cough|pain|anxiety|insomnia|diabetes|cancer|hypertension|arthritis|infection)\b",
    r"\b(detox|cleanse) (my|the body)\b",
    r"\bsubstitute for (rhino|tiger|pangolin)\b",
    r"\bwhere (can|do) i (buy|get|order)\b",
]
DUAL_USE_PATTERNS = [
    r"\bhow (do|can|to) (i |we )?(extract|isolate|synthesi[sz]e|make|prepare|purif(y|ied))\b.*\b(aconit|aristoloch|mercur|arsenic|lead|cinnabar|realgar|bhasma)\w*",
    r"\b(synthesi[sz]e|manufacture|produce)\b.*\b(ricin|abr(us|in)|saxitoxin|tetrodotoxin|botulinum)\b",
    r"\bweaponi[sz]e\b",
    r"\bhow (to|do i) (poison|kill)\b",
    r"\b(prepare|make) (a )?(bhasma|丹|dan)\b.*\b(mercury|arsenic|lead|水銀|砒霜|雄黃)\b",
]


def safety_screen(q: str):
    low = q.lower()
    for p in DUAL_USE_PATTERNS:
        if re.search(p, low):
            return dict(allowed=False, kind="dual_use",
                        reason=("This question asks for preparation or synthesis of a toxic substance. "
                                "SHENNONG analyses hazard in the historical corpus; it does not provide "
                                "synthesis, preparation or weaponisation routes."))
    for p in MED_PATTERNS:
        if re.search(p, low):
            return dict(allowed=False, kind="medical",
                        reason=("This is a personal-use or dosing question. The Workbench is a research "
                                "instrument and cannot give medical advice, dosing or self-treatment "
                                "guidance. Dosing questions belong with a qualified practitioner."))
    return dict(allowed=True, kind=None, reason=None)


CJK = re.compile(r"[\u3400-\u9fff\uf900-\ufaff]")


def _fold(text: str) -> str:
    text = unicodedata.normalize("NFKC", text)
    text = "".join(IAST.get(ch, ch) for ch in text)
    return text.lower()


def tokenize(text: str):
    """CJK unigrams+bigrams; Latin words with light stemming. Stdlib only, no segmenter needed."""
    t = _fold(text)
    toks = []
    for run in re.findall(r"[\u3400-\u9fff\uf900-\ufaff]+|[a-z0-9]+", t):
        if CJK.match(run):
            toks.extend(list(run))
            toks.extend(run[i:i + 2] for i in range(len(run) - 1))
        else:
            if len(run) < 2 or run in STOP:
                continue
            if len(run) > 3 and run.endswith("s") and not run.endswith("ss"):
                run = run[:-1]
            toks.append(run)
    return toks


class BM25:
    def __init__(self, docs, k1=1.35, b=0.72):
        self.k1, self.b = k1, b
        self.docs = docs
        self.toks = [tokenize(d) for d in docs]
        self.lens = [len(t) for t in self.toks]
        self.avg = (sum(self.lens) / len(self.lens)) if self.lens else 1.0
        self.tf = []
        self.df: dict = {}
        for toks in self.toks:
            c: dict = {}
            for tk in toks:
                c[tk] = c.get(tk, 0) + 1
            self.tf.append(c)
            for tk in c:
                self.df[tk] = self.df.get(tk, 0) + 1
        self.N = max(len(docs), 1)

    def idf(self, tk):
        df = self.df.get(tk, 0)
        return math.log(1 + (self.N - df + 0.5) / (df + 0.5))

    def score(self, q_tokens, i):
        s = 0.0
        tf, dl = self.tf[i], self.lens[i]
        for tk in q_tokens:
            f = tf.get(tk)
            if not f:
                continue
            denom = f + self.k1 * (1 - self.b + self.b * dl / self.avg)
            s += self.idf(tk) * f * (self.k1 + 1) / denom
        return s


_INDEX = {"bm25": None, "passages": None, "built_from": None}


def get_index(passages):
    key = id(passages)
    if _INDEX["built_from"] != key:
        _INDEX["bm25"] = BM25([p.get("text", "") for p in passages])
        _INDEX["passages"] = passages
        _INDEX["built_from"] = key
    return _INDEX["bm25"]


def _citation(p, score):
    return dict(passage_id=p.get("id"), source_id=p.get("source_id"), title=p.get("title"),
                title_en=p.get("title_en"), author=p.get("author"), year=p.get("year"),
                tradition=p.get("tradition"), lang=p.get("lang"), tier=p.get("tier"),
                licence=p.get("licence"), span_kind=p.get("span_kind"),
                locator=p.get("locator"), span=p.get("text"), score=round(score, 4))


CJK_SENT = re.compile(r"[^。！？；\n]+[。！？；]?")


def _best_sentences(text, q_tokens, limit=2):
    parts = CJK_SENT.findall(text) if CJK.search(text) else re.split(r"(?<=[.!?;])\s+", text)
    parts = [p.strip() for p in parts if p and p.strip()]
    if len(parts) <= 1:
        return text.strip()
    qt = set(q_tokens)
    scored = sorted(parts, key=lambda s: -len(qt & set(tokenize(s))))
    return " ".join(scored[:limit])


def ask_local(question: str, passages, k=4):
    """Honest extractive retrieval. Returns citations + an answer assembled from the spans."""
    screen = safety_screen(question)
    if not screen["allowed"]:
        return dict(query=question, answer=screen["reason"], citations=[], refused=True,
                    refusal_reason=screen["kind"], confidence=0.0,
                    safety=dict(allowed=False, reasons=[screen["reason"]]),
                    mode="policy-screen")

    if not passages:
        return dict(query=question, answer=("No passage index is loaded, so there is nothing to ground an "
                                            "answer in. Run `make app-data` or check app/data/passages.json."),
                    citations=[], refused=True, refusal_reason="empty-index", confidence=0.0,
                    safety=dict(allowed=True, reasons=[]), mode="no-index")

    q_tokens = tokenize(question)
    if not q_tokens:
        return dict(query=question, answer="That query has no searchable terms.", citations=[],
                    refused=True, refusal_reason="empty-query", confidence=0.0,
                    safety=dict(allowed=True, reasons=[]), mode="local-bm25")

    bm = get_index(passages)
    q_fold = _fold(question)
    q_set = set(q_tokens)

    def source_boost(p):
        """A question that names a text should surface that text. Cheap, explicit, and it makes the
        Ask panel behave the way a scholar expects instead of the way a bag of words does."""
        b = 1.0
        title = _fold(p.get("title") or "")
        if len(title) >= 2 and title in q_fold:
            b *= 1.9
        for w in set(tokenize(p.get("title_en") or "")):
            if len(w) >= 4 and w in q_set:
                b *= 1.25
                break
        return b

    ranked = sorted((((bm.score(q_tokens, i)) * source_boost(passages[i]), i)
                     for i in range(len(passages))), reverse=True)
    top = [(sc, i) for sc, i in ranked[:k] if sc > 0]

    if not top:
        return dict(query=question,
                    answer=("No passage in the indexed corpus mentions those terms. Rather than answer from "
                            "general knowledge — which would not be grounded in this corpus — SHENNONG "
                            "refuses. A refusal is a result: it means the question is outside what the "
                            "loaded texts can support."),
                    citations=[], refused=True, refusal_reason="no-match", confidence=0.0,
                    safety=dict(allowed=True, reasons=[]), mode="local-bm25")

    # Engagement test. Raw token overlap punishes CJK bigrams and common characters, so weight the
    # query's terms by IDF: a passage that matches 三七 must count for more than one matching 本.
    q_set = set(q_tokens)
    idf = {t: bm.idf(t) for t in q_set}
    total_idf = sum(idf.values()) or 1.0
    union = set()
    for _, i in top[:3]:
        union |= set(tokenize(passages[i]["text"]))
    coverage = sum(v for t, v in idf.items() if t in union) / total_idf

    if coverage < 0.22:
        return dict(query=question,
                    answer=(f"The closest passages share only {int(coverage * 100)}% of the query's "
                            "weighted terms. That is too weak to ground a claim, so SHENNONG refuses "
                            "instead of paraphrasing something it cannot support. Try naming a drug, a "
                            "text, a preparation or a discovery class."),
                    citations=[_citation(passages[top[0][1]], top[0][0])], refused=True,
                    refusal_reason="low-coverage", confidence=round(coverage, 3),
                    safety=dict(allowed=True, reasons=[]), mode="local-bm25")

    # Keep only passages that are genuinely in the running: a passage matching one shared word at
    # 20% of the top score contributes noise, not evidence.
    cut = top[0][0] * 0.35
    useful = [(sc, i) for sc, i in top if sc >= cut][:4]

    cits = [_citation(passages[i], sc) for sc, i in useful]
    body = " ".join(f"{_best_sentences(passages[i]['text'], q_tokens)} [{n + 1}]"
                    for n, (sc, i) in enumerate(useful))
    years = sorted({c["year"] for c in cits if isinstance(c.get("year"), int)})
    span = (f"{years[0]}–{years[-1]}" if len(years) > 1 else str(years[0])) if years else "undated"
    head = (f"{len(cits)} passage{'s' if len(cits) > 1 else ''} in the indexed corpus bear on this "
            f"({span}). Extractively, and without adding anything the texts do not say:")
    return dict(query=question, answer=f"{head}\n\n{body}", citations=cits, refused=False,
                refusal_reason=None, confidence=round(min(1.0, coverage * 1.6), 3),
                safety=dict(allowed=True, reasons=[]),
                mode="local-bm25-extractive",
                mode_note=("Local BM25 + extractive span selection. `shennong.rag.answer` was not importable, "
                           "so this is the honest fallback: it quotes and cites, it does not generate."))


_RAG = {"checked": False, "fn": None, "err": None}


def rag_entry():
    if _RAG["checked"]:
        return _RAG["fn"]
    _RAG["checked"] = True
    if ROOT not in sys.path:
        sys.path.insert(0, ROOT)
    try:
        from shennong.rag import answer as _answer  # type: ignore
        _RAG["fn"] = _answer
        note("Ask panel: using shennong.rag.answer (real RAG backend).")
    except Exception as exc:  # noqa: BLE001 - any import problem must fall back, never crash
        _RAG["fn"] = None
        _RAG["err"] = f"{type(exc).__name__}: {exc}"
        note(f"Ask panel: shennong.rag not importable ({_RAG['err']}) — using local BM25 extractive fallback.")
    return _RAG["fn"]


def ask(question: str):
    question = (question or "").strip()[:800]
    if not question:
        return dict(query="", answer="Ask a question about the corpus.", citations=[], refused=True,
                    refusal_reason="empty-query", confidence=0.0,
                    safety=dict(allowed=True, reasons=[]), mode="empty")
    screen = safety_screen(question)
    if not screen["allowed"]:
        return dict(query=question, answer=screen["reason"], citations=[], refused=True,
                    refusal_reason=screen["kind"], confidence=0.0,
                    safety=dict(allowed=False, reasons=[screen["reason"]]), mode="policy-screen")

    fn = rag_entry()
    if fn is not None:
        try:
            res = fn(question, k=5)
            if isinstance(res, dict) and "answer" in res:
                res.setdefault("mode", "shennong.rag")
                res.setdefault("safety", dict(allowed=True, reasons=[]))
                return res
        except Exception as exc:  # noqa: BLE001
            note(f"Ask panel: shennong.rag raised {type(exc).__name__}: {exc} — falling back.")

    passages = load_passages()["passages"]
    return ask_local(question, passages)


# ---------------------------------------------------------------------------------------------
# HTTP
# ---------------------------------------------------------------------------------------------
MIME = {".html": "text/html; charset=utf-8", ".css": "text/css; charset=utf-8",
        ".js": "application/javascript; charset=utf-8", ".json": "application/json; charset=utf-8",
        ".svg": "image/svg+xml", ".png": "image/png", ".ico": "image/x-icon",
        ".woff2": "font/woff2", ".txt": "text/plain; charset=utf-8"}


# ---------------------------------------------------------------------------------------
# Live model query: the MoE, running on the local CPU, behind /api/chat
#
# A judge should be able to type a question and get an answer from the model that was actually trained —
# not from a canned transcript. The checkpoint is loaded lazily (232 MB, a few seconds) and cached, so the
# first query is slow and the rest are not. If the checkpoint is missing the endpoint says so instead of
# pretending, and the UI shows the exact command that trains it.
# ---------------------------------------------------------------------------------------
_MODEL = {"obj": None, "tok": None, "meta": None, "error": None}
_CKPT_CANDIDATES = [
    "training/runs/shennong-moe-r1/ckpt-best.pt",
    "training/runs/shennong-mini-r1/ckpt-best.pt",
    "training/runs/shennong-moe-r1/ckpt.pt",
    "training/runs/shennong-mini-r1/ckpt.pt",
]


DEMO_DIR = os.path.join(ROOT, "docs", "demo")
SERVE_DEMO_AT_ROOT = False


def _serve_demo(handler, rel):
    """Serve the built static demo from /demo/ so the query box is same-origin."""
    safe = os.path.normpath(rel).lstrip("/")
    full = os.path.join(DEMO_DIR, safe)
    if not full.startswith(DEMO_DIR) or not os.path.isfile(full):
        return handler._err(404, "not found")
    ext = os.path.splitext(full)[1].lower()
    ctype = {"html": "text/html; charset=utf-8", "js": "application/javascript",
             "json": "application/json; charset=utf-8", "css": "text/css"}.get(
                 ext.lstrip("."), "application/octet-stream")
    with open(full, "rb") as f:
        return handler._send(200, f.read(), ctype)


def _load_model():
    if _MODEL["obj"] is not None or _MODEL["error"] is not None:
        return _MODEL
    import sys as _sys
    _sys.path.insert(0, os.path.join(ROOT, "model"))
    try:
        from tokenizers import Tokenizer

        from shennong_mini import ModelConfig, ShennongMini, load_checkpoint
        from shennong_moe import MoEConfig, ShennongMoE

        _env_ck = os.environ.get("SHENNONG_CKPT")
        ck_path = (_env_ck if (_env_ck and os.path.isfile(os.path.join(ROOT, _env_ck))) else None) \
            or next((c for c in _CKPT_CANDIDATES if os.path.isfile(os.path.join(ROOT, c))), None)
        if ck_path is None:
            _MODEL["error"] = "no trained checkpoint found — run `make train-mini`"
            return _MODEL
        ck = load_checkpoint(os.path.join(ROOT, ck_path))
        cfg_dict = ck.get("config") or {}
        if int(cfg_dict.get("n_experts", 1)) > 1:
            cfg = MoEConfig.from_dict(cfg_dict)
            model = ShennongMoE(cfg)
            family = "moe"
        else:
            cfg = ModelConfig.from_dict(cfg_dict)
            model = ShennongMini(cfg)
            family = "dense"
        model.load_state_dict(ck["model"], strict=False)
        model.eval()
        tok = Tokenizer.from_file(os.path.join(ROOT, "tokenizer/shennong-bpe/tokenizer.json"))
        _MODEL.update({
            "obj": model, "tok": tok,
            "meta": {
                "checkpoint": ck_path,
                "step": ck.get("step"),
                "family": family,
                "params": sum(p.numel() for p in model.parameters()),
                "active_params": getattr(cfg, "n_params_active", None) if family == "moe" else None,
                "vocab": cfg.vocab_size,
                "context": cfg.seq_len,
                "note": ("Trained from scratch on this machine on a domain-exclusive corpus. It reads "
                         "Classical Chinese, Latin and English. It is a pipeline demonstration, not a "
                         "factual oracle — see model/MODEL_CARD.md."),
            },
        })
    except Exception as exc:  # noqa: BLE001
        _MODEL["error"] = f"{type(exc).__name__}: {exc}"
    return _MODEL


def model_status():
    # The live demo serves the 1.5B GGUF (direct generation + comparison), not the 19 M torch checkpoint.
    gguf = next((g for g in (
        "artifacts/shennong-1.5b-sft-Q4_K_M.gguf",
        "artifacts/shennong-0.5b-sft-Q4_K_M.gguf") if os.path.isfile(os.path.join(ROOT, g))), None)
    if gguf:
        return {"loaded": True, "family": "qwen2-1.5b-sft", "checkpoint": gguf,
                "params": 1543714304, "context": 2048,
                "note": "Live demo: fine-tuned 1.5B GGUF, direct generation with a side-by-side baseline."}
    m = _load_model()
    if m["error"]:
        return {"loaded": False, "error": m["error"]}
    return {"loaded": True, **m["meta"]}


def chat(prompt: str, max_new_tokens: int = 96, temperature: float = 0.8) -> dict:
    """Generate from the trained model. Deterministic given the seed."""
    import time as _t

    import torch

    m = _load_model()
    if m["error"]:
        return {"ok": False, "error": m["error"], "fix": "make train-mini  (or: make train-flagship)"}
    model, tok = m["obj"], m["tok"]
    prompt = (prompt or "").strip()[:2000]
    if not prompt:
        return {"ok": False, "error": "empty prompt"}
    ids = tok.encode(prompt).ids[-model.cfg.seq_len:]
    x = torch.tensor([ids])
    t0 = _t.time()
    with torch.no_grad():
        out = model.generate(x, max_new_tokens=max(1, min(max_new_tokens, 256)),
                             temperature=temperature, top_p=0.9, seed=1337)
    gen = out[0][len(ids):].tolist()
    text = tok.decode(gen)
    return {
        "ok": True,
        "prompt": prompt,
        "completion": text,
        "tokens_generated": len(gen),
        "latency_ms": int((_t.time() - t0) * 1000),
        "model": {k: m["meta"][k] for k in ("checkpoint", "step", "family", "params", "active_params")},
        "honesty": ("This is the model's raw continuation, not a grounded answer. For grounded answers "
                    "with citations use /api/ask, which retrieves first and refuses when it cannot cite."),
    }


class Handler(BaseHTTPRequestHandler):
    server_version = f"ShennongWorkbench/{VERSION}"
    protocol_version = "HTTP/1.1"

    def log_message(self, fmt, *args):  # quieter than the default
        if os.environ.get("SHENNONG_DEBUG"):
            sys.stderr.write("%s - %s\n" % (self.address_string(), fmt % args))

    # --- helpers ---------------------------------------------------------------------------
    def _send(self, code, body: bytes, ctype="application/json; charset=utf-8", cache=False):
        self.send_response(code)
        self.send_header("Content-Type", ctype)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header("Cache-Control", "public, max-age=60" if cache else "no-store")
        self.end_headers()
        try:
            self.wfile.write(body)
        except (BrokenPipeError, ConnectionResetError):
            pass

    def _json(self, obj, code=200):
        self._send(code, json.dumps(obj, ensure_ascii=False).encode("utf-8"))

    def _err(self, code, msg):
        self._json(dict(error=msg, status=code), code)

    # --- routing ---------------------------------------------------------------------------
    def do_OPTIONS(self):
        """CORS preflight. Without this, a browser that preflights a JSON POST gets BaseHTTPRequestHandler's
        501 "unsupported method" and the request dies — which looked like the demo stalling."""
        self.send_response(204)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.send_header("Access-Control-Max-Age", "86400")
        self.send_header("Content-Length", "0")
        self.end_headers()

    def do_GET(self):
        u = urlparse(self.path)
        path = u.path
        q = parse_qs(u.query)
        try:
            if path in ("/", "/index.html"):
                if SERVE_DEMO_AT_ROOT:
                    return _serve_demo(self, "index.html")
                return self._static("index.html")
            if path.startswith("/static/"):
                return self._static(path[len("/static/"):])
            if path == "/favicon.ico":
                return self._send(204, b"")
            if path == "/api/health":
                return self._json(dict(ok=True, version=VERSION))
            if path == "/api/meta":
                return self._json(self._meta())
            if path == "/api/hypotheses":
                return self._json(load_hypotheses())
            if path == "/api/kg":
                return self._json(load_kg())
            if path == "/api/candidates":
                return self._json(load_candidates())
            if path == "/api/corpus":
                return self._json(load_corpus())
            if path == "/api/methodology":
                cand = load_candidates()
                return self._json(dict(eval=load_eval(), metrics=load_metrics(),
                                       pipeline=self._pipeline(),
                                       hypotheses=load_hypotheses()["counts"],
                                       candidates=cand["counts"],
                                       artifacts=load_artifacts()))
            if path == "/api/model":
                return self._json(model_status())
            if path.startswith("/demo"):
                rel = path[len("/demo"):].lstrip("/") or "index.html"
                return _serve_demo(self, rel)
            if path == "/api/ask":
                return self._json(ask((q.get("q") or [""])[0]))
            return self._err(404, f"no route {path}")
        except Exception as exc:  # noqa: BLE001 - the Workbench must never 500 the demo
            import traceback
            traceback.print_exc()
            return self._err(500, f"{type(exc).__name__}: {exc}")

    def do_POST(self):
        u = urlparse(self.path)
        if u.path == "/api/hypothesize":
            try:
                n = int(self.headers.get("Content-Length") or 0)
                raw = self.rfile.read(min(n, 16384)) if n else b"{}"
                payload = json.loads(raw.decode("utf-8") or "{}")
                from shennong.answer import hypothesise_live
                return self._json(hypothesise_live(str(payload.get("question") or payload.get("q") or payload.get("target") or ""),
                                              int(payload.get("k") or 6),
                                              int(payload.get("max_new_tokens") or 96)))
            except Exception as exc:  # noqa: BLE001
                return self._err(500, f"{type(exc).__name__}: {exc}")
        if u.path == "/api/resolve":
            try:
                n = int(self.headers.get("Content-Length") or 0)
                raw = self.rfile.read(min(n, 16384)) if n else b"{}"
                payload = json.loads(raw.decode("utf-8") or "{}")
                from shennong.resolve import resolve_plant
                return self._json(resolve_plant(str(payload.get("question") or payload.get("q") or payload.get("target") or "")))
            except Exception as exc:  # noqa: BLE001
                return self._err(500, f"{type(exc).__name__}: {exc}")
        if u.path == "/api/advise":
            try:
                n = int(self.headers.get("Content-Length") or 0)
                raw = self.rfile.read(min(n, 16384)) if n else b"{}"
                payload = json.loads(raw.decode("utf-8") or "{}")
                from shennong.advise import advise
                return self._json(advise(str(payload.get("question") or payload.get("q") or payload.get("target") or "")))
            except Exception as exc:  # noqa: BLE001
                return self._err(500, f"{type(exc).__name__}: {exc}")
        if u.path == "/api/experts":
            try:
                n = int(self.headers.get("Content-Length") or 0)
                raw = self.rfile.read(min(n, 16384)) if n else b"{}"
                payload = json.loads(raw.decode("utf-8") or "{}")
                from shennong.experts.router import route_query
                return self._json(route_query(str(payload.get("question") or payload.get("q") or payload.get("target") or "")))
            except Exception as exc:  # noqa: BLE001
                return self._err(500, f"{type(exc).__name__}: {exc}")
        if u.path == "/api/screen":
            try:
                n = int(self.headers.get("Content-Length") or 0)
                raw = self.rfile.read(min(n, 16384)) if n else b"{}"
                payload = json.loads(raw.decode("utf-8") or "{}")
                from shennong.screen import fused_screen
                return self._json(fused_screen(str(payload.get("question") or payload.get("q") or payload.get("target") or "COX2"),
                                               top_k=int(payload.get("top_k") or 8)))
            except Exception as exc:  # noqa: BLE001
                return self._err(500, f"{type(exc).__name__}: {exc}")
        if u.path == "/api/compare":
            try:
                n = int(self.headers.get("Content-Length") or 0)
                raw = self.rfile.read(min(n, 16384)) if n else b"{}"
                payload = json.loads(raw.decode("utf-8") or "{}")
                from shennong.answer import compare_direct
                return self._json(compare_direct(str(payload.get("question") or payload.get("q") or payload.get("target") or ""),
                                                 int(payload.get("max_new_tokens") or 56)))
            except Exception as exc:  # noqa: BLE001
                return self._err(500, f"{type(exc).__name__}: {exc}")
        if u.path == "/api/query":
            try:
                n = int(self.headers.get("Content-Length") or 0)
                raw = self.rfile.read(min(n, 16384)) if n else b"{}"
                payload = json.loads(raw.decode("utf-8") or "{}")
                from shennong.moe_serve import answer_moe
                return self._json(answer_moe(str(payload.get("question") or payload.get("q") or payload.get("target") or ""),
                                             max_new_tokens=int(payload.get("max_new_tokens") or 72)))
            except Exception as exc:  # noqa: BLE001
                return self._err(500, f"{type(exc).__name__}: {exc}")
        if u.path == "/api/chat":
            try:
                n = int(self.headers.get("Content-Length") or 0)
                raw = self.rfile.read(min(n, 16384)) if n else b"{}"
                payload = json.loads(raw.decode("utf-8") or "{}")
                return self._json(chat(str(payload.get("prompt") or payload.get("q") or ""),
                                       int(payload.get("max_new_tokens") or 96),
                                       float(payload.get("temperature") or 0.8)))
            except Exception as exc:  # noqa: BLE001
                return self._err(500, f"{type(exc).__name__}: {exc}")
        if u.path != "/api/ask":
            # drain the body first: an unread request body desyncs the keep-alive connection and the next
            # request line is parsed as "{}POST" -> 501 (this is exactly what broke the demo's probes)
            try:
                _n = int(self.headers.get("Content-Length") or 0)
                if _n:
                    self.rfile.read(min(_n, 65536))
            except Exception:  # noqa: BLE001
                pass
            return self._err(404, f"no route {u.path}")
        try:
            n = int(self.headers.get("Content-Length") or 0)
            raw = self.rfile.read(min(n, 8192)) if n else b"{}"
            try:
                payload = json.loads(raw.decode("utf-8") or "{}")
            except json.JSONDecodeError:
                return self._err(400, "body must be JSON")
            return self._json(ask(str(payload.get("question") or payload.get("q") or payload.get("target") or "")))
        except Exception as exc:  # noqa: BLE001
            return self._err(500, f"{type(exc).__name__}: {exc}")

    def _static(self, rel):
        safe = os.path.normpath(rel).lstrip("/")
        full = os.path.join(STATIC_DIR, safe)
        if not full.startswith(STATIC_DIR) or not os.path.isfile(full):
            return self._err(404, "not found")
        ctype = MIME.get(os.path.splitext(full)[1].lower(), "application/octet-stream")
        with open(full, "rb") as f:
            return self._send(200, f.read(), ctype,
                              cache=os.path.splitext(full)[1] in (".svg", ".css", ".js"))

    def _pipeline(self):
        return [
            dict(key="cai", cn="采", py="Cǎi", en="collect",
                 what="Ingest and clean the public-domain Asian classics: Classical Chinese (繁/简), "
                      "Sanskrit (Devanagari + IAST), Arabic/Persian, Tibetan, Japanese/Korean, and open "
                      "translations. Every source carries provenance, licence and tier.",
                 out="corpus.jsonl + registry"),
            dict(key="zhi", cn="制", py="Zhì", en="prepare",
                 what="炮制 for text: normalise orthography and script, resolve drug names across eras and "
                      "languages to modern taxa with a confidence, and translate alchemical process words "
                      "into modern chemistry.",
                 out="lexicon_drugs.json"),
            dict(key="pei", cn="配", py="Pèi", en="combine",
                 what="Assemble the knowledge graph: taxon ↔ compound ↔ target ↔ indication, formula "
                      "composition with 君臣佐使 roles, and the 十八反/十九畏/viruddha incompatibility edges.",
                 out="kg.json"),
            dict(key="shi", cn="使", py="Shǐ", en="deploy",
                 what="Rank hypotheses inside six discovery classes, attach a falsification plan and an "
                      "uncertainty note to every one, and publish the negative controls beside the results.",
                 out="hypotheses.json + eval/report.json"),
        ]

    def _meta(self):
        h = load_hypotheses()
        c = load_corpus()
        e = load_eval()
        m = load_metrics()
        k = load_kg()
        p = load_passages()
        cand = load_candidates()
        status = [
            dict(key="hypotheses", label="Hypotheses (使 Shǐ)", fixture=h["fixture"], source=h["source"],
                 detail=f"{h['counts'].get('total', 0)} ranked · {h['counts'].get('classes', 0)} classes"),
            dict(key="candidates", label="Drug candidates (使 Shǐ)", fixture=cand["fixture"],
                 source=cand["source"],
                 detail=f"{cand['counts'].get('total', 0)} candidates · "
                        f"{cand['counts'].get('resolved', 0)} with resolved structures"),
            dict(key="kg", label="Knowledge graph (配 Pèi)", fixture=k["fixture"], source=k["source"],
                 detail=f"{len(k['nodes'])} nodes · {len(k['edges'])} edges"),
            dict(key="passages", label="Passage index (采 Cǎi)", fixture=p["fixture"], source=p["source"],
                 detail=f"{len(p['passages'])} passages"),
            dict(key="corpus", label="Corpus ledger", fixture=c["fixture"], source=c["source"],
                 detail=f"{c['stats']['kept']} sources kept · {c['stats']['excluded']} excluded"),
            dict(key="eval", label="Evaluation (使 Shǐ)", fixture=e["fixture"], source=e["source"],
                 detail=("negative controls + benchmarks" if not e["fixture"]
                         else "DEMO FIXTURE twin — awaiting eval/report.json")),
            dict(key="metrics", label="Training run", fixture=m["fixture"], source=m["source"],
                 detail="loss curve available" if not m["fixture"] else "awaiting training runs"),
        ]
        return dict(name=NAME, name_cn=NAME_CN, tagline=TAGLINE, version=VERSION,
                    pipeline=PIPELINE, status=status,
                    fixture_count=sum(1 for s in status if s["fixture"]),
                    live_count=sum(1 for s in status if not s["fixture"]),
                    any_fixture=any(s["fixture"] for s in status),
                    rag_backend=("shennong.rag" if rag_entry() else "local-bm25-fallback"),
                    now=datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"))


# ---------------------------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------------------------
def pick_port(preferred: int) -> int:
    for p in [preferred] + list(range(preferred + 1, preferred + 20)):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            try:
                s.bind(("127.0.0.1", p))
                return p
            except OSError:
                continue
    return 0


def build_report():
    h = load_hypotheses()
    c = load_corpus()
    e = load_eval()
    m = load_metrics()
    k = load_kg()
    p = load_passages()
    cand = load_candidates()
    rows = [
        ("candidates", cand["source"], cand["fixture"],
         f"{cand['counts'].get('total', 0)} candidates"),
        ("hypotheses", h["source"], h["fixture"], f"{h['counts'].get('total', 0)} ranked"),
        ("kg", k["source"], k["fixture"], f"{len(k['nodes'])} nodes / {len(k['edges'])} edges"),
        ("passages", p["source"], p["fixture"], f"{len(p['passages'])} passages"),
        ("corpus", c["source"], c["fixture"], f"{c['stats']['kept']} kept / {c['stats']['excluded']} excluded"),
        ("eval", e["source"], e["fixture"],
         "loaded" if not e["fixture"] else "DEMO FIXTURE twin"),
        ("metrics", m["source"], m["fixture"],
         "loaded" if not m["fixture"] else "absent — no fabricated curve"),
    ]
    return rows


def _warm():
    """Load the model and the retrieval index in the background, so the first judge click is not a 60 s wait."""
    try:
        from shennong.answer import _model
        from shennong.rag.answer import get_index
        get_index()
        _model()
        print("   warm: retrieval index + model loaded", flush=True)
    except Exception as exc:  # noqa: BLE001
        print(f"   warm: skipped ({type(exc).__name__}: {exc})", flush=True)


def main(argv=None):
    ap = argparse.ArgumentParser(description="SHENNONG Workbench")
    ap.add_argument("--port", type=int, default=8765)
    ap.add_argument("--demo-root", action="store_true",
                    help="serve the built judge demo at / (used when hosting the demo)")
    ap.add_argument("--host", default="127.0.0.1")
    ap.add_argument("--open", action="store_true", help="open a browser window")
    ap.add_argument("--strict", action="store_true",
                    help="refuse to start if any panel would show DEMO FIXTURE data")
    args = ap.parse_args(argv)

    try:  # show the banner immediately even when stdout is a pipe or a log file
        sys.stdout.reconfigure(line_buffering=True)
    except (AttributeError, ValueError):
        pass

    rows = build_report()
    fixtures = [r for r in rows if r[2]]

    print("  ▁▁▁▁▁▁▁▁▁▁▁▁▁▁▁▁▁▁▁▁▁▁▁▁▁▁▁▁▁▁▁▁▁▁▁▁▁▁▁▁▁▁▁▁▁▁▁▁▁▁▁▁▁▁▁▁", flush=True)
    print(f"   {NAME} {NAME_CN}  ·  Workbench v{VERSION}")
    print("  ▔▔▔▔▔▔▔▔▔▔▔▔▔▔▔▔▔▔▔▔▔▔▔▔▔▔▔▔▔▔▔▔▔▔▔▔▔▔▔▔▔▔▔▔▔▔▔▔▔▔▔▔▔▔▔▔▔")
    for key, source, fixture, detail in rows:
        mark = "FIXTURE" if fixture else "REAL   "
        print(f"   {key:<11} {mark}  {detail:<28} {source}")
    if fixtures:
        print()
        print(f"   ⚠  {len(fixtures)}/{len(rows)} panels are showing DEMO FIXTURE data.")
        print("      Fixtures exist so the UI can be built before the pipeline lands.")
        print("      Run `make app-data` to replace them, then reload. `--strict` refuses fixtures.")
    else:
        print("\n   ✓ all panels on real artefacts")
    if args.strict and fixtures:
        print("\n   ✗ --strict: refusing to start on fixture data.\n")
        return 2

    port = pick_port(args.port)
    url = f"http://{args.host}:{port}/"
    import threading
    threading.Thread(target=_warm, daemon=True).start()

    global SERVE_DEMO_AT_ROOT
    SERVE_DEMO_AT_ROOT = bool(args.demo_root)
    if SERVE_DEMO_AT_ROOT:
        print(f"   demo root: serving {DEMO_DIR} at /")

    httpd = ThreadingHTTPServer((args.host, port), Handler)
    httpd.daemon_threads = True
    print(f"\n   → open  {url}\n   → Ctrl-C to stop\n")
    if args.open:
        threading.Timer(0.6, lambda: webbrowser.open(url)).start()
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\n   stopped.\n")
    finally:
        httpd.server_close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
