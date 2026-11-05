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


def load_corpus():
    ypath = os.path.join(ROOT, "corpus", "registry", "sources.yaml")
    rows = normalise_sources(parse_sources_yaml(ypath))
    if rows:
        return _summarise_corpus(rows, "corpus/registry/sources.yaml", False)
    fx = _read_json(os.path.join(DATA_DIR, "corpus.json"))
    rows = normalise_sources((fx or {}).get("sources"))
    if rows:
        return _summarise_corpus(rows, "app/data/corpus.json", True,
                                 built=(fx or {}).get("built"), stages=(fx or {}).get("stages"))
    return _summarise_corpus([], "(missing)", True)


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
                           year_min=min(years) if years else None, year_max=max(years) if years else None))


def load_eval():
    real = os.path.join(ROOT, "eval", "report.json")
    d = _read_json(real)
    if isinstance(d, dict) and d.get("benchmarks") is not None:
        return dict(report=d, fixture=False, source="eval/report.json",
                    generated_at=d.get("generated_at"))
    # No measured evaluation yet. Show the panel's structure with an explicit empty state rather
    # than inventing benchmark numbers — the negative controls are the whole point of that panel.
    return dict(report=None, fixture=True, source="(no eval/report.json)",
                awaiting="python -m shennong.cli report --out eval/report.json")


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
    def do_GET(self):
        u = urlparse(self.path)
        path = u.path
        q = parse_qs(u.query)
        try:
            if path in ("/", "/index.html"):
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
            if path == "/api/corpus":
                return self._json(load_corpus())
            if path == "/api/methodology":
                return self._json(dict(eval=load_eval(), metrics=load_metrics(),
                                       pipeline=self._pipeline(), hypotheses=load_hypotheses()["counts"]))
            if path == "/api/ask":
                return self._json(ask((q.get("q") or [""])[0]))
            return self._err(404, f"no route {path}")
        except Exception as exc:  # noqa: BLE001 - the Workbench must never 500 the demo
            import traceback
            traceback.print_exc()
            return self._err(500, f"{type(exc).__name__}: {exc}")

    def do_POST(self):
        u = urlparse(self.path)
        if u.path != "/api/ask":
            return self._err(404, f"no route {u.path}")
        try:
            n = int(self.headers.get("Content-Length") or 0)
            raw = self.rfile.read(min(n, 8192)) if n else b"{}"
            try:
                payload = json.loads(raw.decode("utf-8") or "{}")
            except json.JSONDecodeError:
                return self._err(400, "body must be JSON")
            return self._json(ask(str(payload.get("question") or payload.get("q") or "")))
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
        status = [
            dict(key="hypotheses", label="Hypotheses (使 Shǐ)", fixture=h["fixture"], source=h["source"],
                 detail=f"{h['counts'].get('total', 0)} ranked · {h['counts'].get('classes', 0)} classes"),
            dict(key="kg", label="Knowledge graph (配 Pèi)", fixture=k["fixture"], source=k["source"],
                 detail=f"{len(k['nodes'])} nodes · {len(k['edges'])} edges"),
            dict(key="passages", label="Passage index (采 Cǎi)", fixture=p["fixture"], source=p["source"],
                 detail=f"{len(p['passages'])} passages"),
            dict(key="corpus", label="Corpus ledger", fixture=c["fixture"], source=c["source"],
                 detail=f"{c['stats']['kept']} sources kept · {c['stats']['excluded']} excluded"),
            dict(key="eval", label="Evaluation (使 Shǐ)", fixture=e["fixture"], source=e["source"],
                 detail="negative controls + benchmarks" if not e["fixture"] else "awaiting eval/report.json"),
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
    rows = [
        ("hypotheses", h["source"], h["fixture"], f"{h['counts'].get('total', 0)} ranked"),
        ("kg", k["source"], k["fixture"], f"{len(k['nodes'])} nodes / {len(k['edges'])} edges"),
        ("passages", p["source"], p["fixture"], f"{len(p['passages'])} passages"),
        ("corpus", c["source"], c["fixture"], f"{c['stats']['kept']} kept / {c['stats']['excluded']} excluded"),
        ("eval", e["source"], e["fixture"], "loaded" if not e["fixture"] else "absent — panel shows empty state"),
        ("metrics", m["source"], m["fixture"], "loaded" if not m["fixture"] else "absent — no fabricated curve"),
    ]
    return rows


def main(argv=None):
    ap = argparse.ArgumentParser(description="SHENNONG Workbench")
    ap.add_argument("--port", type=int, default=8765)
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
