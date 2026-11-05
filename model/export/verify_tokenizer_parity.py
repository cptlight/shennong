"""Verify that a GGUF's tokenizer reproduces the HuggingFace tokenizer used in training.

This is the check that separates "the file parses" from "the file works". `llama.cpp` does not
run the HF `tokenizers` library; it re-implements pre-tokenization + BPE from the vocab, merge
list and a named `tokenizer.ggml.pre` regex. Any mismatch silently changes the token stream the
model was trained on.

This script:
  1. reads the GGUF with `gguf.GGUFReader` (vocab, merges, `tokenizer.ggml.pre`);
  2. re-implements llama.cpp's GPT-2 path exactly — same pre-tokenizer regex as
     `src/llama-vocab.cpp` (`LLAMA_VOCAB_PRE_TYPE_GPT2`), same GPT-2 byte↔unicode alphabet,
     same greedy lowest-rank BPE merge;
  3. encodes held-out corpus chunks with both implementations and reports
     **token-id exact-match rate** and the token-count ratio.

Usage
-----
    python model/export/verify_tokenizer_parity.py \
        --gguf artifacts/shennong-mini-f16.gguf \
        --tokenizer tokenizer/shennong-bpe/tokenizer.json \
        --corpus corpus/processed/corpus.jsonl --n 60
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import regex as re

# llama.cpp src/llama-vocab.cpp, case LLAMA_VOCAB_PRE_TYPE_GPT2
LLAMA_CPP_GPT2_PRE = r"'s|'t|'re|'ve|'m|'ll|'d| ?\p{L}+| ?\p{N}+| ?[^\s\p{L}\p{N}]+|\s+(?!\S)|\s+"


def bytes_to_unicode() -> dict[int, str]:
    """GPT-2 reversible byte -> unicode-codepoint alphabet (same table `tokenizers` uses)."""
    bs = (list(range(ord("!"), ord("~") + 1)) + list(range(ord("¡"), ord("¬") + 1))
          + list(range(ord("®"), ord("ÿ") + 1)))
    cs = bs[:]
    n = 0
    for b in range(256):
        if b not in bs:
            bs.append(b)
            cs.append(256 + n)
            n += 1
    return dict(zip(bs, (chr(c) for c in cs)))


B2U = bytes_to_unicode()


class LlamaCppGpt2:
    """Minimal re-implementation of llama.cpp's gpt-2 tokenizer path."""

    def __init__(self, tokens: list[str], merges: list[str], pre: str = LLAMA_CPP_GPT2_PRE):
        self.token_to_id = {t: i for i, t in enumerate(tokens)}
        self.ranks = {}
        for rank, m in enumerate(merges):
            parts = m.split(" ")
            if len(parts) == 2:
                self.ranks[(parts[0], parts[1])] = rank
        self.re = re.compile(pre)

    def _bpe(self, word: str) -> list[str]:
        # word is already in byte-level unicode alphabet
        parts = list(word)
        if len(parts) == 1:
            return parts
        while True:
            best_rank, best_i = None, -1
            for i in range(len(parts) - 1):
                r = self.ranks.get((parts[i], parts[i + 1]))
                if r is not None and (best_rank is None or r < best_rank):
                    best_rank, best_i = r, i
            if best_rank is None:
                return parts
            pair = (parts[best_i], parts[best_i + 1])
            merged, out, i = "", [], 0
            while i < len(parts):
                if i < len(parts) - 1 and (parts[i], parts[i + 1]) == pair:
                    out.append(parts[i] + parts[i + 1])
                    i += 2
                else:
                    out.append(parts[i])
                    i += 1
            parts = out

    def encode(self, text: str) -> list[int]:
        ids: list[int] = []
        for m in self.re.finditer(text):
            piece = m.group(0)
            word = "".join(B2U[b] for b in piece.encode("utf-8"))
            for tok in self._bpe(word):
                tid = self.token_to_id.get(tok)
                if tid is None:  # llama.cpp emits <unk>; should never happen for byte-level BPE
                    raise KeyError(f"token {tok!r} missing from GGUF vocab")
                ids.append(tid)
        return ids


def read_gguf_vocab(path: Path):
    import gguf

    r = gguf.GGUFReader(str(path))
    tokens_f = r.get_field("tokenizer.ggml.tokens")
    merges_f = r.get_field("tokenizer.ggml.merges")
    pre_f = r.get_field("tokenizer.ggml.pre")

    # gguf-py 0.19's ReaderField.contents() mis-decodes arrays of strings (it indexes the
    # length part instead of the bytes part). Decode from the raw `parts` instead:
    # for a string array, field.data[i] is the index of the i-th string's *bytes* part.
    def as_str_list(field):
        return [bytes(field.parts[i]).decode("utf-8") for i in field.data]

    tokens = as_str_list(tokens_f)
    merges = as_str_list(merges_f) if merges_f is not None else []
    pre = bytes(pre_f.parts[-1]).decode("utf-8") if pre_f is not None else "default"
    return tokens, merges, pre


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--gguf", required=True)
    ap.add_argument("--tokenizer", default="tokenizer/shennong-bpe/tokenizer.json")
    ap.add_argument("--corpus", default="corpus/processed/corpus.jsonl")
    ap.add_argument("--n", type=int, default=60, help="held-out chunks per language")
    ap.add_argument("--out", default="", help="optional JSON report path")
    args = ap.parse_args()

    from tokenizers import Tokenizer

    hf = Tokenizer.from_file(args.tokenizer)
    tokens, merges, pre = read_gguf_vocab(Path(args.gguf))
    print(f"GGUF: {len(tokens):,} tokens, {len(merges):,} merges, tokenizer.ggml.pre={pre!r}")
    if pre != "gpt-2":
        print(f"WARNING: pre is {pre!r}, not 'gpt-2'; parity test assumes the GPT-2 regex",
              file=sys.stderr)
    llama = LlamaCppGpt2(tokens, merges)

    # held-out chunks, balanced per language
    by_lang: dict[str, list[str]] = {}
    with open(args.corpus, encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if not line:
                continue
            try:
                rec = json.loads(line)
            except json.JSONDecodeError:
                continue
            text = rec.get("text") or ""
            lang = rec.get("lang", "?")
            if len(text) >= 300:
                by_lang.setdefault(lang, []).append(text)

    report = {"gguf": args.gguf, "pre": pre, "n_tokens": len(tokens), "n_merges": len(merges),
              "per_language": {}}
    overall_exact, overall_total = 0, 0
    for lang in sorted(by_lang):
        docs = by_lang[lang][:args.n]
        exact = 0
        n_hf = n_ll = 0
        mismatch_example = None
        n_bytes = 0
        for d in docs:
            a = hf.encode(d).ids
            b = llama.encode(d)
            n_hf += len(a)
            n_ll += len(b)
            n_bytes += len(d.encode("utf-8"))
            if a == b:
                exact += 1
            elif mismatch_example is None:
                for i, (x, y) in enumerate(zip(a, b)):
                    if x != y:
                        mismatch_example = {"first_diff_index": i,
                                            "hf_token": a[i], "llama_token": b[i],
                                            "hf_tokens_around": a[max(0, i - 2):i + 3],
                                            "llama_tokens_around": b[max(0, i - 2):i + 3],
                                            "decoded_context": d[:120]}
                        break
        rep = {
            "docs": len(docs),
            "exact_match_docs": exact,
            "exact_match_rate": round(exact / max(len(docs), 1), 4),
            "hf_tokens": n_hf,
            "llama_tokens": n_ll,
            "token_count_ratio": round(n_ll / max(n_hf, 1), 4),
            "bytes": n_bytes,
            "mismatch_example": mismatch_example,
        }
        report["per_language"][lang] = rep
        overall_exact += exact
        overall_total += len(docs)
        print(f"{lang:8s} docs={len(docs):3d} exact={exact:3d} ({rep['exact_match_rate']*100:5.1f}%)  "
              f"llama/hf tokens={rep['token_count_ratio']:.4f}")
        if mismatch_example:
            print(f"         first mismatch: {mismatch_example}")

    report["overall_exact_match_rate"] = round(overall_exact / max(overall_total, 1), 4)
    report["overall_docs"] = overall_total
    print(f"\nOVERALL exact-match: {overall_exact}/{overall_total} "
          f"= {report['overall_exact_match_rate']*100:.2f}%")

    if args.out:
        Path(args.out).parent.mkdir(parents=True, exist_ok=True)
        Path(args.out).write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n",
                                  encoding="utf-8")
        print(f"wrote {args.out}")
    return 0 if report["overall_exact_match_rate"] >= 0.95 else 1


if __name__ == "__main__":
    raise SystemExit(main())
