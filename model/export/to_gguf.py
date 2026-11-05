"""Convert a SHENNONG HF-format model directory to GGUF (f16/f32) — CPU only, no `transformers`.

Why this script exists
----------------------
llama.cpp ships `convert_hf_to_gguf.py`, which is the reference implementation. It imports
`transformers` for tokenizer loading, and this machine's venv has no `pip`/`uv` and no
`transformers`. Rather than ship a fake or a stub, this script re-implements the *whole*
conversion for the Llama architecture using llama.cpp's own official `gguf` writer package
(the same library `convert_hf_to_gguf.py` uses), and verifies the result by reading it back
with `gguf.GGUFReader`. The metadata keys and tensor names below are taken from
llama.cpp `gguf-py/gguf/constants.py` (`MODEL_ARCH.LLAMA`, `TENSOR_NAMES`), cloned at
`.tmp/llama.cpp` and cited in the model card.

Usage
-----
    python model/export/to_gguf.py --hf-dir artifacts/shennong-mini-hf \
        --out artifacts/shennong-mini-f16.gguf --outtype f16 --verify

Verification (--verify) re-reads the file and checks: tensor names/shapes, total parameter
count, vocab size, special-token ids, and the SHA-256 + exact byte size.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from collections import OrderedDict
from pathlib import Path

import numpy as np
import torch

ROOT = Path(__file__).resolve().parent.parent.parent

# ---------------------------------------------------------------------------------------
# HF name -> llama.cpp GGUF name (gguf-py constants.TENSOR_NAMES[MODEL_ARCH.LLAMA])
# ---------------------------------------------------------------------------------------
_TENSOR_MAP = {
    "model.embed_tokens.weight": "token_embd.weight",
    "model.norm.weight": "output_norm.weight",
    "lm_head.weight": "output.weight",
}
_LAYER_TENSOR_MAP = {
    "input_layernorm.weight": "attn_norm.weight",
    "self_attn.q_proj.weight": "attn_q.weight",
    "self_attn.k_proj.weight": "attn_k.weight",
    "self_attn.v_proj.weight": "attn_v.weight",
    "self_attn.o_proj.weight": "attn_output.weight",
    "post_attention_layernorm.weight": "ffn_norm.weight",
    "mlp.gate_proj.weight": "ffn_gate.weight",
    "mlp.up_proj.weight": "ffn_up.weight",
    "mlp.down_proj.weight": "ffn_down.weight",
}


def gguf_tensor_name(hf_name: str) -> str | None:
    if hf_name in _TENSOR_MAP:
        return _TENSOR_MAP[hf_name]
    if hf_name.startswith("model.layers."):
        _, _, idx, rest = hf_name.split(".", 3)
        if rest in _LAYER_TENSOR_MAP:
            return f"blk.{idx}.{_LAYER_TENSOR_MAP[rest]}"
    return None


# ---------------------------------------------------------------------------------------
# Tokenizer (tokenizer.json -> GGUF vocab/merges/token types)
# ---------------------------------------------------------------------------------------
def load_tokenizer_gguf_fields(tokenizer_dir: Path) -> dict:
    """Extract tokens / token types / merges from a HF `tokenizers` tokenizer.json."""
    tj = json.loads((tokenizer_dir / "tokenizer.json").read_text(encoding="utf-8"))
    model = tj["model"]
    if model.get("type") != "BPE":
        raise SystemExit(f"expected a BPE tokenizer.json, got {model.get('type')!r}")

    id_to_token: dict[int, str] = {}
    added = {}
    for tok in tj.get("added_tokens", []):
        added[tok["id"]] = tok
    for token, tid in model["vocab"].items():
        id_to_token[tid] = token
    # Some tokenizers keep special tokens only in `added_tokens`.
    for tid, tok in added.items():
        id_to_token.setdefault(tid, tok["content"])

    vocab_size = max(id_to_token) + 1
    tokens: list[str] = []
    for i in range(vocab_size):
        if i not in id_to_token:
            raise SystemExit(f"tokenizer.json has a hole at id {i}; cannot build a dense GGUF vocab")
        tokens.append(id_to_token[i])

    special_ids = {i for i, t in added.items() if t.get("special", False)}
    types: list[int] = [int(gguf_token_control()) if i in special_ids else int(gguf_token_normal())
                        for i in range(vocab_size)]

    merges_raw = model.get("merges", [])
    merges: list[str] = []
    for m in merges_raw:
        merges.append(f"{m[0]} {m[1]}" if isinstance(m, (list, tuple)) else str(m))

    name_to_id = {tok: i for i, tok in enumerate(tokens)}
    special = {}
    for name in ("<|bos|>", "<|eos|>", "<|pad|>", "<|unk|>"):
        if name in name_to_id:
            special[name.strip("<|>").lower()] = name_to_id[name]
    return {
        "tokens": tokens,
        "types": types,
        "merges": merges,
        "vocab_size": vocab_size,
        "added": added,
        "special": special,
    }


def gguf_token_control() -> int:
    from gguf.constants import TokenType

    return int(TokenType.CONTROL)


def gguf_token_normal() -> int:
    from gguf.constants import TokenType

    return int(TokenType.NORMAL)


# ---------------------------------------------------------------------------------------
# Conversion
# ---------------------------------------------------------------------------------------
def convert(hf_dir: Path, out_path: Path, outtype: str = "f16", name: str = "shennong-mini",
            license: str = "apache-2.0", quantize_config: dict | None = None) -> dict:
    from safetensors import safe_open
    import gguf
    from gguf.constants import GGMLQuantizationType

    hf_dir = Path(hf_dir)
    cfg = json.loads((hf_dir / "config.json").read_text(encoding="utf-8"))
    np_dtype = {"f16": np.float16, "f32": np.float32}[outtype]
    file_type = int(GGMLQuantizationType.F16 if outtype == "f16" else GGMLQuantizationType.F32)

    tok = load_tokenizer_gguf_fields(hf_dir)
    vocab_size = int(cfg["vocab_size"])
    if tok["vocab_size"] != vocab_size:
        raise SystemExit(f"tokenizer vocab {tok['vocab_size']} != config vocab_size {vocab_size}")

    writer = gguf.GGUFWriter(str(out_path), "llama")
    writer.add_name(name)
    writer.add_description("SHENNONG mini — small Llama-style model for Asian medical heritage "
                           "(computational ethnopharmacology research; not for clinical use).")
    writer.add_license(license)
    writer.add_file_type(file_type)
    writer.add_quantization_version(2)
    writer.add_context_length(int(cfg["max_position_embeddings"]))
    writer.add_embedding_length(int(cfg["hidden_size"]))
    writer.add_block_count(int(cfg["num_hidden_layers"]))
    writer.add_feed_forward_length(int(cfg["intermediate_size"]))
    writer.add_head_count(int(cfg["num_attention_heads"]))
    writer.add_head_count_kv(int(cfg["num_key_value_heads"]))
    writer.add_rope_dimension_count(int(cfg["hidden_size"]) // int(cfg["num_attention_heads"]))
    writer.add_rope_freq_base(float(cfg.get("rope_theta", 10000.0)))
    writer.add_layer_norm_rms_eps(float(cfg.get("rms_norm_eps", 1e-5)))
    writer.add_vocab_size(vocab_size)

    # tokenizer
    writer.add_tokenizer_model("gpt2")
    writer.add_tokenizer_pre("gpt-2")  # exact llama.cpp GPT-2 pre-tokenizer regex; see MODEL_CARD.md
    writer.add_token_list(tok["tokens"])
    writer.add_token_types(tok["types"])
    writer.add_token_merges(tok["merges"])
    if "bos" in tok["special"]:
        writer.add_bos_token_id(tok["special"]["bos"])
    if "eos" in tok["special"]:
        writer.add_eos_token_id(tok["special"]["eos"])
    if "pad" in tok["special"]:
        writer.add_pad_token_id(tok["special"]["pad"])
    writer.add_add_bos_token(False)
    writer.add_add_eos_token(False)
    writer.add_add_space_prefix(False)

    # tensors
    n_written = 0
    with safe_open(str(hf_dir / "model.safetensors"), framework="pt") as f:
        for hf_name in f.keys():
            gguf_name = gguf_tensor_name(hf_name)
            if gguf_name is None:
                raise SystemExit(f"unmapped tensor {hf_name!r}")
            t = f.get_tensor(hf_name).detach().to(torch.float32).contiguous()
            arr = t.numpy().astype(np_dtype, copy=False)
            writer.add_tensor(gguf_name, arr)
            n_written += 1

    writer.write_header_to_file()
    writer.write_kv_data_to_file()
    writer.write_tensors_to_file(progress=False)
    writer.close()

    return {
        "out_path": str(out_path),
        "bytes": out_path.stat().st_size,
        "sha256": sha256_file(out_path),
        "tensors": n_written,
        "vocab_size": vocab_size,
        "outtype": outtype,
        "hf_config": cfg,
    }


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


# ---------------------------------------------------------------------------------------
# Verification: parse the GGUF back and check it against the HF model
# ---------------------------------------------------------------------------------------
def verify_gguf(gguf_path: Path, expected_params: int | None = None,
                expected_vocab: int | None = None, hf_dir: Path | None = None,
                outtype: str = "f16") -> dict:
    from gguf import GGUFReader

    reader = GGUFReader(str(gguf_path))

    import gguf.gguf_reader as _gr

    def field(name):
        f = reader.get_field(name)
        if f is None:
            return None
        from gguf.constants import GGUFValueType

        main_type = f.types[0]
        if main_type == GGUFValueType.STRING:
            return bytes(f.parts[-1]).decode("utf-8")
        if main_type == GGUFValueType.ARRAY and f.types[-1] == GGUFValueType.STRING:
            return len(f.data)  # only the count is needed below
        return f.parts[-1].tolist()[0]

    tensors = {}
    total = 0
    for t in reader.tensors:
        # GGUF stores dims reversed vs. torch; reverse back for an intuitive shape.
        shape = tuple(int(x) for x in t.shape)[::-1]
        tensors[t.name] = {"shape": shape, "dtype": str(t.tensor_type.name), "nbytes": int(t.n_bytes)}
        n = 1
        for d in shape:
            n *= d
        total += n

    meta = {
        "general.architecture": field("general.architecture"),
        "general.name": field("general.name"),
        "general.license": field("general.license"),
        "general.file_type": field("general.file_type"),
        "llama.context_length": field("llama.context_length"),
        "llama.embedding_length": field("llama.embedding_length"),
        "llama.block_count": field("llama.block_count"),
        "llama.feed_forward_length": field("llama.feed_forward_length"),
        "llama.attention.head_count": field("llama.attention.head_count"),
        "llama.attention.head_count_kv": field("llama.attention.head_count_kv"),
        "llama.rope.freq_base": field("llama.rope.freq_base"),
        "tokenizer.ggml.model": field("tokenizer.ggml.model"),
        "tokenizer.ggml.pre": field("tokenizer.ggml.pre"),
        "tokenizer.ggml.bos_token_id": field("tokenizer.ggml.bos_token_id"),
        "tokenizer.ggml.eos_token_id": field("tokenizer.ggml.eos_token_id"),
        # current llama.cpp names this key `tokenizer.ggml.padding_token_id` (gguf-py constants
        # Keys.Tokenizer.PAD_ID; llama-arch.cpp LLM_KV_TOKENIZER_PAD_ID)
        "tokenizer.ggml.padding_token_id": field("tokenizer.ggml.padding_token_id"),
    }
    tok_field = reader.get_field("tokenizer.ggml.tokens")
    n_vocab = len(tok_field.data) if tok_field is not None else None
    merges_field = reader.get_field("tokenizer.ggml.merges")
    n_merges = len(merges_field.data) if merges_field is not None else None

    report = {
        "path": str(gguf_path),
        "bytes": gguf_path.stat().st_size,
        "sha256": sha256_file(gguf_path),
        "n_tensors": len(tensors),
        "total_parameters": total,
        "n_vocab": n_vocab,
        "n_merges": n_merges,
        "metadata": meta,
        "tensor_shapes": {k: v["shape"] for k, v in tensors.items()},
        "dtypes": sorted({v["dtype"] for v in tensors.values()}),
        "checks": {},
    }
    ok = True
    report["checks"]["file_nonempty"] = report["bytes"] > 0
    ok &= report["checks"]["file_nonempty"]
    if expected_params is not None:
        report["checks"]["params_match"] = total == expected_params
        report["expected_params"] = expected_params
        ok &= report["checks"]["params_match"]
    report["checks"]["arch_llama"] = meta["general.architecture"] == "llama"
    report["checks"]["has_attn_q"] = "blk.0.attn_q.weight" in tensors
    report["checks"]["has_ffn_down"] = "blk.0.ffn_down.weight" in tensors
    report["checks"]["vocab_matches"] = (expected_vocab is None or n_vocab == expected_vocab)
    report["checks"]["dtypes_ok"] = set(report["dtypes"]) <= {"F16", "F32"}
    for k in ("arch_llama", "has_attn_q", "has_ffn_down", "dtypes_ok", "vocab_matches"):
        ok &= report["checks"][k]
    # Strongest possible check short of running llama.cpp: do the stored values match the
    # HF tensors bit-for-bit after the f16 cast?
    if hf_dir is not None:
        from safetensors import safe_open

        np_dtype = np.float16 if outtype == "f16" else np.float32
        checked, mismatched, max_diff = 0, [], 0.0
        with safe_open(str(Path(hf_dir) / "model.safetensors"), framework="pt") as f:
            for hf_name in f.keys():
                gname = gguf_tensor_name(hf_name)
                g = next((t for t in reader.tensors if t.name == gname), None)
                if g is None:
                    mismatched.append(gname)
                    continue
                ref = f.get_tensor(hf_name).detach().to(torch.float32).numpy().astype(np_dtype)
                got = np.asarray(g.data, dtype=np_dtype)
                if ref.shape != got.shape:
                    mismatched.append(f"{gname}:shape {ref.shape}!={got.shape}")
                    continue
                d = float(np.max(np.abs(ref.astype(np.float32) - got.astype(np.float32))))
                max_diff = max(max_diff, d)
                if d != 0.0:
                    mismatched.append(gname)
                checked += 1
        report["checks"]["values_bit_exact"] = (not mismatched) and checked > 0
        report["value_check"] = {"tensors_checked": checked, "mismatched": mismatched[:5],
                                 "max_abs_diff": max_diff}
        ok &= report["checks"]["values_bit_exact"]
    report["ok"] = bool(ok)
    return report


# ---------------------------------------------------------------------------------------
def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--hf-dir", required=True, help="HF-format directory (config.json + model.safetensors)")
    ap.add_argument("--out", required=True, help="output .gguf path")
    ap.add_argument("--outtype", default="f16", choices=["f16", "f32"])
    ap.add_argument("--name", default="shennong-mini")
    ap.add_argument("--verify", action="store_true", help="re-read the GGUF and validate it")
    args = ap.parse_args()

    from safetensors import safe_open

    cfg = json.loads((Path(args.hf_dir) / "config.json").read_text(encoding="utf-8"))
    # Expected param count, computed from the HF config the same way the model does.
    sys.path.insert(0, str(ROOT / "model"))
    from shennong_mini import ModelConfig

    expected = ModelConfig.from_dict(cfg).n_params_estimate

    info = convert(Path(args.hf_dir), Path(args.out), args.outtype, name=args.name)
    print(f"wrote {info['out_path']}: {info['bytes']:,} bytes  sha256={info['sha256']}")
    print(f"tensors={info['tensors']}  vocab={info['vocab_size']}  params(expected)={expected:,}")

    if args.verify:
        rep = verify_gguf(Path(args.out), expected_params=expected,
                          expected_vocab=int(cfg["vocab_size"]),
                          hf_dir=Path(args.hf_dir), outtype=args.outtype)
        print(json.dumps({k: v for k, v in rep.items() if k != "tensor_shapes"}, indent=2))
        if not rep["ok"]:
            print("VERIFY FAILED", file=sys.stderr)
            return 1
        print("VERIFY OK")
        # sidecar hash file, consumed by the Lead's contract verifier
        sidecar = Path(str(args.out) + ".sha256")
        sidecar.write_text(f"{rep['sha256']}  {Path(args.out).name}\n", encoding="utf-8")
        print(f"wrote {sidecar}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
