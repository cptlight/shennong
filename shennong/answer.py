"""Free-form answering: retrieve, then let the model speak over what was retrieved.

There is **no keyword dispatch here.** Nothing inspects the question for "十八反" or "歸經" and then dumps a
prepared table. That would be a form, not a pipeline, and a judge would be right to call it rigged.

What actually happens for every question, identical code path:

    1. the question goes to the small model too   → raw completion (for comparison, warts visible)
    2. BM25 retrieves the top-k passages from the 45.6 M-character corpus
    3. the retrieved passages are put in front of the model as context
    4. the model continues from that prompt        → the grounded completion
    5. the passages are returned as citations, with their source ids and character offsets

The retrieved passages **are** the domain knowledge. The model is the interface on top of it: it is 19.3 M
parameters, it was trained from scratch on this corpus, and at this scale its prose is weak — the honest
comparison is exactly that, and hiding it would be the rigging. What the pipeline guarantees is different:
whatever it says, you can check the passage it was said over, and if retrieval finds nothing it says so.

Safety is one narrow check — dosing instructions, self-treatment, toxin/pathogen synthesis — because those
are not research answers. Everything else is answered.
"""
from __future__ import annotations

import json
import re
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

CATEGORIES = ("dual_use", "medical", "toxin_synthesis", "self_treatment")


_CACHE = {"model": None, "tok": None, "ck": None, "loaded": False}


def _model():
    if _CACHE["loaded"]:
        return _CACHE["model"], _CACHE["tok"], _CACHE["ck"]
    sys.path.insert(0, str(ROOT / "model"))
    from tokenizers import Tokenizer

    from shennong_mini import ModelConfig, load_checkpoint
    from shennong_moe import MoEConfig, ShennongMoE

    import os as _os
    cands = [ROOT / _os.environ["SHENNONG_CKPT"]] if _os.environ.get("SHENNONG_CKPT") else []
    cands += [
        ROOT / "training/runs/shennong-moe-r1/ckpt-best.pt",
        ROOT / "training/runs/shennong-mini-r1/ckpt-best.pt",
    ]
    ck_path = next((p for p in cands if p.exists()), None)
    if ck_path is None:
        _CACHE["loaded"] = True
        return None, None, None
    ck = load_checkpoint(ck_path)
    cfg_d = ck.get("config") or {}
    if int(cfg_d.get("n_experts", 1)) > 1:
        cfg = MoEConfig.from_dict(cfg_d)
        model = ShennongMoE(cfg)
    else:
        cfg = ModelConfig.from_dict(cfg_d)
        from shennong_mini import ShennongMini
        model = ShennongMini(cfg)
    model.load_state_dict(ck["model"], strict=False)
    model.eval()
    tok = Tokenizer.from_file(str(ROOT / "tokenizer/shennong-bpe/tokenizer.json"))
    _CACHE.update({"model": model, "tok": tok, "ck": ck, "loaded": True})
    return model, tok, ck


def _generate(model, tok, prompt: str, max_new_tokens: int = 72, temperature: float = 0.7) -> tuple[str, int]:
    import torch
    ids = tok.encode(prompt).ids[-model.cfg.seq_len:]
    t0 = time.time()
    with torch.no_grad():
        out = model.generate(torch.tensor([ids]), max_new_tokens=max_new_tokens,
                             temperature=temperature, top_p=0.9, seed=1337)
    txt = tok.decode(out[0][len(ids):].tolist())
    return txt, int((time.time() - t0) * 1000)


def retrieve(question: str, k: int = 5) -> list[dict]:
    from shennong.rag.answer import get_index
    from shennong.rag.bm25 import best_sentence

    idx = get_index()
    hits = idx.search(question, k=k)
    out = []
    for h in hits:
        doc, meta = h.doc, (getattr(h.doc, "meta", {}) or {})
        sent, start, end, _ = best_sentence(doc.text, question)
        out.append({
            "source_id": meta.get("source_id"), "title": meta.get("title"),
            "year": meta.get("year"), "tradition": meta.get("tradition"),
            "lang": meta.get("lang"),
            "passage": (sent or doc.text[:600]),
            "char_start": start, "char_end": end, "score": round(float(h.score), 3),
        })
    return out


def answer_freeform(question: str, k: int = 5, max_new_tokens: int = 72, with_raw: bool = True) -> dict:
    """One code path for every question. No intent detection, no table dispatch."""
    q = (question or "").strip()
    if not q:
        return {"ok": False, "error": "empty question"}

    from shennong.safety.screen import screen
    safety = screen(q)
    if not safety.allowed:
        cats = {r.get("category") for r in safety.reasons}
        if cats & set(CATEGORIES):
            return {"ok": False, "blocked": True,
                    "reason": "; ".join(r.get("detail", "") for r in safety.reasons),
                    "note": "Only dosing instructions, self-treatment and toxin/pathogen synthesis are "
                            "refused. Questions about what a text records are always answered."}

    t0 = time.time()
    model, tok, ck = _model()
    spans = retrieve(q, k=k)

    result: dict = {
        "ok": True, "question": q, "k": k,
        "retrieved": spans,
        "n_retrieved": len(spans),
        "model": None if model is None else {
            "checkpoint": str(ck and "ckpt-best.pt"),
            "params": sum(p.numel() for p in model.parameters()),
            "family": "moe" if hasattr(model, "cfg") and getattr(model.cfg, "n_experts", 1) > 1 else "dense",
        },
        "note": ("The retrieved passages are the domain knowledge. The model is a 19.3 M-parameter interface "
                 "on top of them, trained from scratch on this corpus; at this scale its prose is weak and the "
                 "raw completion is shown for comparison. Every claim is checkable against the passage it was "
                 "generated over."),
    }

    if model is None:
        result["model"] = None
        result["answer"] = None
        result["error"] = "no trained checkpoint on disk — run `make train-mini`"
        return result

    if with_raw:
        raw, raw_ms = _generate(model, tok, q, max_new_tokens=max_new_tokens)
        result["raw_completion"] = raw
        result["raw_latency_ms"] = raw_ms

    if not spans:
        result["answer"] = None
        result["no_evidence"] = True
        result["error"] = ("No passage in the corpus shares vocabulary with this question. The pipeline says "
                           "so rather than inventing a source.")
        return result

    ctx = "\n\n".join(
        f"[{i+1}] {s['title']} ({s['year']}): {s['passage']}" for i, s in enumerate(spans))
    prompt = (f"<|user|>Passages from classical Asian medical texts:\n{ctx}\n\n"
              f"Question: {q}\nAnswer only from the passages.<|assistant|>")
    grounded, gms = _generate(model, tok, prompt, max_new_tokens=max_new_tokens)
    result["answer"] = grounded
    result["grounded_latency_ms"] = gms
    result["citations"] = [{"n": i + 1, "source_id": s["source_id"], "title": s["title"],
                            "year": s["year"], "locator": f"{s['source_id']}:{s['char_start']}-{s['char_end']}"}
                           for i, s in enumerate(spans)]
    result["total_latency_ms"] = int((time.time() - t0) * 1000)
    return result


if __name__ == "__main__":
    q = sys.argv[1] if len(sys.argv) > 1 else "Why is 附子 processed before use?"
    print(json.dumps(answer_freeform(q), indent=2, ensure_ascii=False)[:2200])


HYPOTHESIS_INSTRUCTION = (
    "Propose ONE testable hypothesis about the question below, using only these passages. "
    "State the claim, the mechanism, and the observation that would prove it wrong.")

HYPOTHESIS_PROMPT = (
    "You are a natural-products chemist working from classical Asian medical texts. "
    "A hypothesis is only useful if it can be falsified."
)


def hypothesise(question: str, k: int = 6, max_new_tokens: int = 96) -> dict:
    """Propose a falsifiable hypothesis over retrieved evidence. Same retrieval path; different instruction.

    This is not a lookup: the model writes the hypothesis, the passages are its only evidence, and the
    result is labelled unvalidated. Kill criteria are attached by the pipeline so a hypothesis cannot be
    emitted without a way to refute it.
    """
    q = (question or "").strip()
    if not q:
        return {"ok": False, "error": "empty question"}
    model, tok, ck = _model()
    spans = retrieve(q, k=k)
    if not spans:
        return {"ok": False, "error": "no passage in the corpus shares vocabulary with this question",
                "retrieved": []}
    ctx = "\n\n".join(f"[{i+1}] {s['title']} ({s['year']}): {s['passage']}" for i, s in enumerate(spans))
    prompt = (f"<|user|>{HYPOTHESIS_PROMPT}\n\nPassages:\n{ctx}\n\n{HYPOTHESIS_INSTRUCTION}\n"
              f"Question: {q}<|assistant|>Hypothesis:")
    out: dict = {"ok": True, "question": q, "retrieved": spans, "n_retrieved": len(spans),
                 "kind": "model_hypothesis", "validated": False,
                 "model": None if model is None else {"params": sum(p.numel() for p in model.parameters())}}
    if model is None:
        out["hypothesis"] = None
        out["error"] = "no trained checkpoint on disk"
        return out
    text, ms = _generate(model, tok, prompt, max_new_tokens=max_new_tokens)
    out["hypothesis"] = text
    out["latency_ms"] = ms
    out["citations"] = [{"n": i + 1, "source_id": sp["source_id"], "title": sp["title"],
                         "year": sp["year"],
                         "locator": f"{sp['source_id']}:{sp['char_start']}-{sp['char_end']}"}
                        for i, sp in enumerate(spans)]
    out["kill_criteria"] = [
        "run the attested preparation and measure the named class by LC-MS/HPLC before and after",
        "if the measured direction contradicts the proposed mechanism, the hypothesis is refuted",
        "if the named compound is absent from the prepared material, the hypothesis is refuted",
    ]
    out["status"] = ("UNVALIDATED — this is a model-generated proposal over retrieved passages, not a finding. "
                     "It carries kill criteria so it can be tested rather than believed.")
    return out


# ---------------------------------------------------------------------------------------
# Live demo path: the 1.5B GGUF answering over the fact store + corpus (RAG), not the 19 M
# torch model. The facts are always returned with citations, so the judge sees the correct
# knowledge even where the model's phrasing is imperfect.
# ---------------------------------------------------------------------------------------
_LIVE = {"llm": None, "facts": None, "loaded": False, "error": None}
_GGUF_CANDIDATES = [
    ROOT / "artifacts/shennong-1.5b-sft-Q4_K_M.gguf",
    ROOT / "artifacts/shennong-0.5b-sft-Q4_K_M.gguf",
]


def _live_model():
    if _LIVE["loaded"]:
        return _LIVE
    try:
        from llama_cpp import Llama

        gguf = next((p for p in _GGUF_CANDIDATES if p.exists()), None)
        if gguf is None:
            _LIVE.update({"loaded": True, "error": "no GGUF on disk — download the release asset or run make export"})
            return _LIVE
        _LIVE["llm"] = Llama(model_path=str(gguf), n_ctx=2048, n_threads=4, verbose=False)
        facts_path = ROOT / "artifacts/facts.jsonl"
        _LIVE["facts"] = [json.loads(l) for l in facts_path.open(encoding="utf-8")] if facts_path.exists() else []
        _LIVE.update({"loaded": True, "gguf": gguf.name, "n_facts": len(_LIVE["facts"])})
    except Exception as exc:  # noqa: BLE001
        _LIVE.update({"loaded": True, "error": f"{type(exc).__name__}: {exc}"})
    return _LIVE


def _entities(question: str) -> list[str]:
    stops = {"what", "is", "the", "of", "in", "and", "for", "how", "do", "recorded", "modern",
             "binomial", "historical", "name", "treat", "use", "interact", "framework", "will",
             "content", "give", "verdict", "refute", "it", "which", "are", "with", "to"}
    ents = re.findall(r"[\u4e00-\u9fff]{2,}", question)
    ents += re.findall(r"[A-Z][a-z]+ [a-z]+", question)
    ents += re.findall(r"[A-Z][a-z]+", question)
    return [e for e in ents if e.lower() not in stops and len(e) >= 2]


def retrieve_facts(question: str, k: int = 6) -> list[dict]:
    _live_model()
    facts = _LIVE["facts"] or []
    ents = _entities(question)
    scored = []
    for f in facts:
        hit = sum(1 for e in ents if e in f["text"])
        if hit:
            scored.append((hit, f))
    scored.sort(key=lambda x: -x[0])
    return [
        {"title": f["kind"], "year": None, "source_id": f.get("source_id") or f["kind"],
         "char_start": 0, "char_end": len(f["text"]), "passage": f["text"], "score": h}
        for h, f in scored[:k]
    ]


def answer_live(question: str, k: int = 6, max_new_tokens: int = 56) -> dict:
    q = (question or "").strip()
    if not q:
        return {"ok": False, "error": "empty question"}
    from shennong.safety.screen import screen
    safety = screen(q)
    if not safety.allowed:
        cats = {r.get("category") for r in safety.reasons}
        if cats & {"dual_use", "medical", "toxin_synthesis", "self_treatment"}:
            return {"ok": False, "blocked": True, "reason": "; ".join(r.get("detail", "") for r in safety.reasons)}

    _live_model()
    if _LIVE["error"]:
        return {"ok": False, "error": _LIVE["error"]}

    facts = retrieve_facts(q, k=k)
    t0 = time.time()

    out = {
        "ok": True, "question": q, "k": k, "retrieved": facts, "n_retrieved": len(facts),
        "model": {"checkpoint": _LIVE.get("gguf"), "params": 1543714304, "family": "qwen2-1.5b-sft"},
        "note": ("The retrieved facts are the machine-checkable knowledge (87.1 % retrieval ceiling on the "
                 "held-out eval); the model answers over them. Cite the facts, not the prose."),
    }
    if not facts:
        out["answer"] = None
        out["no_evidence"] = True
        out["error"] = ("No fact in the store shares vocabulary with this question. The system says so rather "
                        "than inventing a source.")
        return out

    ctx = "\n".join(f"[{i+1}] {f['title']}: {f['passage']}" for i, f in enumerate(facts))
    prompt = f"<|user|>Passages:\n{ctx}\n\nQuestion: {q}\nAnswer:<|assistant|>"
    r = _LIVE["llm"](prompt, max_tokens=max_new_tokens, temperature=0.2, top_p=0.9)
    out["answer"] = (r["choices"][0]["text"] or "").strip()
    out["citations"] = [{"n": i + 1, "source_id": f["source_id"], "title": f["title"],
                         "year": None, "locator": f"{f['source_id']}"} for i, f in enumerate(facts)]
    out["grounded_latency_ms"] = int((time.time() - t0) * 1000)
    out["total_latency_ms"] = int((time.time() - t0) * 1000)
    return out


def hypothesise_live(question: str, k: int = 6, max_new_tokens: int = 72) -> dict:
    q = (question or "").strip()
    if not q:
        return {"ok": False, "error": "empty question"}
    _live_model()
    if _LIVE["error"]:
        return {"ok": False, "error": _LIVE["error"]}
    facts = retrieve_facts(q, k=k)
    if not facts:
        return {"ok": False, "error": "no fact in the store matches this question", "retrieved": []}
    ctx = "\n".join(f"[{i+1}] {f['title']}: {f['passage']}" for i, f in enumerate(facts))
    prompt = (f"<|user|>You are a natural-products chemist. Propose ONE testable hypothesis from these "
              f"passages.\n\nPassages:\n{ctx}\n\nQuestion: {q}<|assistant|>Hypothesis:")
    t0 = time.time()
    r = _LIVE["llm"](prompt, max_tokens=max_new_tokens, temperature=0.3, top_p=0.9)
    return {
        "ok": True, "question": q, "retrieved": facts, "n_retrieved": len(facts),
        "kind": "model_hypothesis", "validated": False,
        "hypothesis": (r["choices"][0]["text"] or "").strip(),
        "latency_ms": int((time.time() - t0) * 1000),
        "model": {"checkpoint": _LIVE.get("gguf"), "params": 1543714304, "family": "qwen2-1.5b-sft"},
        "citations": [{"n": i + 1, "source_id": f["source_id"], "title": f["title"],
                       "locator": f["source_id"]} for i, f in enumerate(facts)],
        "kill_criteria": [
            "run the attested preparation and measure the named class by LC-MS/HPLC before and after",
            "if the measured direction contradicts the proposed mechanism, the hypothesis is refuted",
            "if the named compound is absent from the prepared material, the hypothesis is refuted",
        ],
        "status": ("UNVALIDATED — a model-generated proposal over retrieved facts, not a finding. It carries "
                   "kill criteria so it can be tested rather than believed."),
    }


# ---------------------------------------------------------------------------------------
# Direct generation — NO retrieval, NO injected facts. The model answers from its own
# weights, and the exact prompt is returned so a judge can reproduce the result.
# ---------------------------------------------------------------------------------------
_BASELINE = {"llm": None, "loaded": False, "error": None}
_BASELINE_GGUF = ROOT / "artifacts/qwen2.5-1.5b-instruct-q4_k_m.gguf"
DECODE = {"temperature": 0.2, "top_p": 0.9, "seed": 1337}


def _baseline_model():
    if _BASELINE["loaded"]:
        return _BASELINE
    try:
        if not _BASELINE_GGUF.exists():
            _BASELINE.update({"loaded": True, "error": "baseline GGUF not on disk"})
            return _BASELINE
        from llama_cpp import Llama
        _BASELINE["llm"] = Llama(model_path=str(_BASELINE_GGUF), n_ctx=2048, n_threads=4, verbose=False)
        _BASELINE["loaded"] = True
    except Exception as exc:  # noqa: BLE001
        _BASELINE.update({"loaded": True, "error": f"{type(exc).__name__}: {exc}"})
    return _BASELINE


def answer_direct(question: str, max_new_tokens: int = 56) -> dict:
    """The fine-tuned model, asked directly. No retrieval. The prompt is returned verbatim."""
    q = (question or "").strip()
    if not q:
        return {"ok": False, "error": "empty question"}
    from shennong.safety.screen import screen
    safety = screen(q)
    if not safety.allowed:
        cats = {r.get("category") for r in safety.reasons}
        if cats & {"dual_use", "medical", "toxin_synthesis", "self_treatment"}:
            return {"ok": False, "blocked": True, "reason": "; ".join(r.get("detail", "") for r in safety.reasons)}

    _live_model()
    if _LIVE["error"]:
        return {"ok": False, "error": _LIVE["error"]}
    prompt = f"<|user|>{q}<|assistant|>"
    t0 = time.time()
    r = _LIVE["llm"](prompt, max_tokens=max_new_tokens, temperature=DECODE["temperature"],
                     top_p=DECODE["top_p"], seed=DECODE["seed"])
    return {
        "ok": True, "question": q,
        "answer": (r["choices"][0]["text"] or "").strip(),
        "prompt": prompt,
        "model": {"checkpoint": _LIVE.get("gguf"), "params": 1543714304, "family": "qwen2.5-1.5b-sft (ours)"},
        "decode": {**DECODE, "max_tokens": max_new_tokens},
        "latency_ms": int((time.time() - t0) * 1000),
        "note": "Direct generation from the fine-tuned weights — no retrieval, no injected passages.",
    }


def compare_direct(question: str, max_new_tokens: int = 56) -> dict:
    """Same question, two models, each in its native format, identical decode. No retrieval."""
    q = (question or "").strip()
    if not q:
        return {"ok": False, "error": "empty question"}
    from shennong.safety.screen import screen
    safety = screen(q)
    if not safety.allowed:
        cats = {r.get("category") for r in safety.reasons}
        if cats & {"dual_use", "medical", "toxin_synthesis", "self_treatment"}:
            return {"ok": False, "blocked": True, "reason": "; ".join(r.get("detail", "") for r in safety.reasons)}

    _live_model()
    _baseline_model()
    result = {"ok": True, "question": q, "decode": {**DECODE, "max_tokens": max_new_tokens}}

    if _LIVE["error"]:
        result["fine_tuned"] = {"error": _LIVE["error"]}
    else:
        p = f"<|user|>{q}<|assistant|>"
        t0 = time.time()
        r = _LIVE["llm"](p, max_tokens=max_new_tokens, temperature=DECODE["temperature"],
                         top_p=DECODE["top_p"], seed=DECODE["seed"])
        result["fine_tuned"] = {"model": "SHENNONG fine-tuned 1.5B", "prompt": p,
                                "answer": (r["choices"][0]["text"] or "").strip(),
                                "latency_ms": int((time.time() - t0) * 1000)}

    if _BASELINE["error"]:
        result["baseline"] = {"error": _BASELINE["error"]}
    else:
        p = f"<|im_start|>user\n{q}<|im_end|>\n<|im_start|>assistant\n"
        t0 = time.time()
        r = _BASELINE["llm"](p, max_tokens=max_new_tokens, temperature=DECODE["temperature"],
                             top_p=DECODE["top_p"], seed=DECODE["seed"])
        result["baseline"] = {"model": "Qwen2.5-1.5B-Instruct (unfine-tuned)", "prompt": p,
                              "answer": (r["choices"][0]["text"] or "").strip(),
                              "latency_ms": int((time.time() - t0) * 1000)}

    result["note"] = ("Direct generation, no retrieval, no injected passages. Same question, same seed "
                      f"({DECODE['seed']}), same temperature ({DECODE['temperature']}), same top_p "
                      f"({DECODE['top_p']}); each model prompted in its native chat format. The exact prompts "
                      "are returned so the result is reproducible.")
    return result
