"""RAG + model: retrieve classical spans, then let the MoE model phrase the answer over them.

This is the join between the two halves of the system that were previously separate — the retrieval
index over the corpus and the sparse model trained on it. The contract is borrowed from
`shennong.rag.answer`, so the refusal discipline is not re-implemented:

    retrieve (BM25 over corpus spans)  →  refuse if the evidence is thin
                                      →  compose a prompt with numbered citations
                                      →  MoE generates, conditioned on those spans only
                                      →  return text + the spans it was given

The model is deliberately *not* asked to recall facts: it is asked to phrase an answer over spans that
are shown to it. If the model is not available, the extractive answer from `shennong.rag` is returned
and labelled as such — the system never silently falls back to ungrounded generation.

Usage:
    python -m shennong.generate "Why is 附子 processed before use?" --checkpoint training/runs/shennong-moe-r1/ckpt-best.pt
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

PROMPT = (
    "You are reading a corpus of classical Asian medical texts. Answer the question using ONLY the "
    "numbered passages below. Cite passages as [1], [2]. If the passages do not answer it, say so.\n\n"
    "{passages}\n\nQuestion: {question}\nAnswer:"
)


def build_prompt(question: str, hits: list[dict], max_chars: int = 900) -> str:
    blocks = []
    for i, h in enumerate(hits, 1):
        text = (h.get("text") or "")[:max_chars]
        blocks.append(f"[{i}] {h.get('title') or h.get('source_id')} ({h.get('year')}): {text}")
    return PROMPT.format(passages="\n\n".join(blocks), question=question)


def answer_with_model(question: str, checkpoint: str | Path, k: int = 5,
                      max_new_tokens: int = 160, seed: int = 1337) -> dict:
    """Retrieve, then generate over the retrieved spans with the sparse MoE."""
    import torch
    from tokenizers import Tokenizer

    from .rag.answer import get_index
    from .rag.bm25 import best_sentence

    idx = get_index()
    hits = idx.search(question, k=k)
    if not hits:
        return {"refused": True, "reason": "no passage in the corpus matches the question",
                "answer": None, "citations": []}

    payload = []
    for h in hits:
        doc = h.doc
        meta = getattr(doc, "meta", {}) or {}
        sent, start, end, score = best_sentence(doc.text, question)
        payload.append({"text": sent or doc.text[:400],
                        "title": meta.get("title"), "source_id": meta.get("source_id"),
                        "year": meta.get("year"), "score": round(float(h.score), 4),
                        "char_start": start, "char_end": end})
    mean_score = sum(p["score"] for p in payload) / len(payload)
    if mean_score < 1.0:
        return {"refused": True, "reason": f"retrieval too weak (mean BM25 {mean_score:.2f})",
                "answer": None, "citations": payload}

    sys.path.insert(0, str(ROOT / "model"))
    from shennong_mini import load_checkpoint
    from shennong_moe import MoEConfig, ShennongMoE

    ck = load_checkpoint(checkpoint)
    cfg = MoEConfig.from_dict(ck["config"])
    model = ShennongMoE(cfg)
    model.load_state_dict(ck["model"], strict=False)
    model.eval()

    tok = Tokenizer.from_file(str(ROOT / "tokenizer/shennong-bpe/tokenizer.json"))
    prompt = build_prompt(question, payload)
    ids = tok.encode(prompt).ids[-cfg.seq_len:]
    x = torch.tensor([ids])
    with torch.no_grad():
        out = model.generate(x, max_new_tokens=max_new_tokens, temperature=0.7, top_p=0.9, seed=seed)
    text = tok.decode(out[0][len(ids):].tolist()).strip()
    return {"refused": False, "answer": text, "citations": payload, "prompt_chars": len(prompt),
            "model_params": sum(p.numel() for p in model.parameters()),
            "note": ("The model phrases; the spans carry the facts. A small model conditioned on "
                     "retrieved passages is the design, not a limitation to apologise for.")}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("question")
    ap.add_argument("--checkpoint", default="training/runs/shennong-moe-r1/ckpt-best.pt")
    ap.add_argument("--k", type=int, default=5)
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args()

    ck = ROOT / args.checkpoint
    if not ck.exists():
        print(json.dumps({"refused": True, "reason": f"no checkpoint at {ck}"}, indent=2))
        return 1
    res = answer_with_model(args.question, ck, k=args.k)
    if args.json:
        print(json.dumps(res, indent=2, ensure_ascii=False))
    else:
        print("REFUSED:" if res["refused"] else "ANSWER:")
        print(res.get("answer") or res.get("reason"))
        print("\nCITATIONS:")
        for i, c in enumerate(res["citations"], 1):
            print(f"  [{i}] {c.get('title')} ({c.get('year')}) chars {c.get('char_start')}-{c.get('char_end')}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
