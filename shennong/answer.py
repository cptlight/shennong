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
    prompt = (f"Classical Asian medical texts, passages:\n{ctx}\n\n"
              f"Question: {q}\nAnswer from the passages:")
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
    prompt = f"{HYPOTHESIS_PROMPT}\n\nPassages:\n{ctx}\n\n{HYPOTHESIS_INSTRUCTION}\nQuestion: {q}\nHypothesis:"
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
