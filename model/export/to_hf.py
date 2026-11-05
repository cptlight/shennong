"""Export a SHENNONG checkpoint to HuggingFace-compatible format (no `transformers` needed).

Produces a directory that `transformers.LlamaForCausalLM.from_pretrained` can load on any
machine, and that `convert_hf_to_gguf.py` understands:

    <out_dir>/config.json
    <out_dir>/model.safetensors
    <out_dir>/tokenizer.json / tokenizer_config.json / special_tokens_map.json

The state-dict layout of `shennong_mini.ShennongMini` is re-mapped to the HF Llama naming
convention, and tied embeddings are stored once (HF Llama omits `lm_head.weight` when
`tie_word_embeddings` is true, and llama.cpp then ties `output.weight` to `token_embd.weight`).

Usage
-----
    python model/export/to_hf.py --checkpoint training/runs/<run>/ckpt_best.pt \
                                 --tokenizer tokenizer/shennong-bpe \
                                 --out artifacts/shennong-mini-hf
"""

from __future__ import annotations

import argparse
import json
import shutil
import sys
from collections import OrderedDict
from pathlib import Path

import torch

ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(ROOT / "model"))

from shennong_mini import ModelConfig, ShennongMini  # noqa: E402

SPECIAL_TOKENS = ["<|pad|>", "<|bos|>", "<|eos|>", "<|system|>", "<|user|>", "<|assistant|>"]

# ShennongMini state-dict name -> HF Llama state-dict name


def load_model(checkpoint: str | Path) -> ShennongMini:
    """Load a training checkpoint ({"model":..., "config":..., "step":...}) into a model."""
    payload = torch.load(checkpoint, map_location="cpu")
    if isinstance(payload, dict) and "model" in payload and "config" in payload:
        cfg = ModelConfig.from_dict(payload["config"])
        model = ShennongMini(cfg)
        missing, unexpected = model.load_state_dict(payload["model"], strict=False)
        # Only the tied embedding alias may legitimately be "missing".
        missing = [m for m in missing if m != "lm_head.weight"]
        if missing or unexpected:
            raise RuntimeError(f"checkpoint mismatch: missing={missing} unexpected={unexpected}")
    elif isinstance(payload, dict):  # bare state_dict
        raise SystemExit("checkpoint has no config; pass --config <json> and use --state-dict mode")
    else:
        raise SystemExit(f"unrecognised checkpoint format: {type(payload)}")
    model.eval()
    return model


def hf_state_dict(model: ShennongMini) -> OrderedDict[str, torch.Tensor]:
    """Re-map ShennongMini keys to HF Llama keys (explicit, no reflection tricks)."""
    sd = OrderedDict()
    sd["model.embed_tokens.weight"] = model.tok_emb.weight.detach().contiguous().clone()
    for i, layer in enumerate(model.layers):
        p = f"model.layers.{i}."
        sd[p + "input_layernorm.weight"] = layer.attn_norm.weight.detach().contiguous().clone()
        sd[p + "self_attn.q_proj.weight"] = layer.attn.q_proj.weight.detach().contiguous().clone()
        sd[p + "self_attn.k_proj.weight"] = layer.attn.k_proj.weight.detach().contiguous().clone()
        sd[p + "self_attn.v_proj.weight"] = layer.attn.v_proj.weight.detach().contiguous().clone()
        sd[p + "self_attn.o_proj.weight"] = layer.attn.o_proj.weight.detach().contiguous().clone()
        sd[p + "post_attention_layernorm.weight"] = layer.mlp_norm.weight.detach().contiguous().clone()
        sd[p + "mlp.gate_proj.weight"] = layer.mlp.gate_proj.weight.detach().contiguous().clone()
        sd[p + "mlp.up_proj.weight"] = layer.mlp.up_proj.weight.detach().contiguous().clone()
        sd[p + "mlp.down_proj.weight"] = layer.mlp.down_proj.weight.detach().contiguous().clone()
    sd["model.norm.weight"] = model.norm.weight.detach().contiguous().clone()
    if not model.cfg.tie_word_embeddings:
        sd["lm_head.weight"] = model.lm_head.weight.detach().contiguous().clone()
    return sd


_HF_TO_NATIVE_LAYER = {
    "input_layernorm.weight": "attn_norm.weight",
    "self_attn.q_proj.weight": "attn.q_proj.weight",
    "self_attn.k_proj.weight": "attn.k_proj.weight",
    "self_attn.v_proj.weight": "attn.v_proj.weight",
    "self_attn.o_proj.weight": "attn.o_proj.weight",
    "post_attention_layernorm.weight": "mlp_norm.weight",
    "mlp.gate_proj.weight": "mlp.gate_proj.weight",
    "mlp.up_proj.weight": "mlp.up_proj.weight",
    "mlp.down_proj.weight": "mlp.down_proj.weight",
}


def hf_to_native_name(hf_name: str) -> str | None:
    """Inverse of hf_state_dict(): HF Llama key -> ShennongMini state-dict key."""
    if hf_name == "model.embed_tokens.weight":
        return "tok_emb.weight"
    if hf_name == "model.norm.weight":
        return "norm.weight"
    if hf_name == "lm_head.weight":
        return "lm_head.weight"
    if hf_name.startswith("model.layers."):
        _, _, idx, rest = hf_name.split(".", 3)
        native = _HF_TO_NATIVE_LAYER.get(rest)
        return f"layers.{idx}.{native}" if native else None
    return None


def load_hf_model(hf_dir: str | Path, dtype: torch.dtype = torch.float32) -> ShennongMini:
    """Load a HF-format directory written by write_hf() back into a ShennongMini."""
    from safetensors import safe_open

    hf_dir = Path(hf_dir)
    cfg = ModelConfig.from_dict(json.loads((hf_dir / "config.json").read_text(encoding="utf-8")))
    model = ShennongMini(cfg)
    sd = {}
    with safe_open(str(hf_dir / "model.safetensors"), framework="pt") as f:
        for name in f.keys():
            native = hf_to_native_name(name)
            if native is None:
                raise SystemExit(f"unmapped HF tensor {name!r}")
            sd[native] = f.get_tensor(name).to(dtype)
    missing, unexpected = model.load_state_dict(sd, strict=False)
    missing = [m for m in missing if m not in ("lm_head.weight", "tok_emb.weight")]
    if missing or unexpected:
        raise RuntimeError(f"HF load mismatch: missing={missing} unexpected={unexpected}")
    model.eval()
    return model


def hf_config_dict(model: ShennongMini, tokenizer_dir: Path | None, dtype: str = "float32") -> dict:
    cfg = model.cfg
    bos_id, eos_id, pad_id = 1, 2, 0
    if tokenizer_dir is not None:
        from tokenizers import Tokenizer

        tok = Tokenizer.from_file(str(Path(tokenizer_dir) / "tokenizer.json"))
        vocab = tok.get_vocab()
        for name, var in (("<|bos|>", "bos"), ("<|eos|>", "eos"), ("<|pad|>", "pad")):
            if name in vocab:
                if var == "bos":
                    bos_id = vocab[name]
                elif var == "eos":
                    eos_id = vocab[name]
                else:
                    pad_id = vocab[name]
    return {
        "architectures": ["LlamaForCausalLM"],
        "model_type": "llama",
        "vocab_size": cfg.vocab_size,
        "hidden_size": cfg.d_model,
        "intermediate_size": cfg.d_ff,
        "num_hidden_layers": cfg.n_layer,
        "num_attention_heads": cfg.n_head,
        "num_key_value_heads": cfg.n_kv_head,
        "hidden_act": "silu",
        "max_position_embeddings": cfg.seq_len,
        "initializer_range": cfg.init_std,
        "rms_norm_eps": cfg.norm_eps,
        "use_cache": True,
        "rope_theta": cfg.rope_theta,
        "tie_word_embeddings": cfg.tie_word_embeddings,
        "attention_bias": cfg.attention_bias,
        "torch_dtype": dtype,
        "bos_token_id": bos_id,
        "eos_token_id": eos_id,
        "pad_token_id": pad_id,
        "transformers_version": "n/a (custom export)",
    }


def write_hf(model: ShennongMini, out_dir: str | Path, tokenizer_dir: str | Path | None = None,
             dtype: torch.dtype = torch.float32) -> dict:
    from safetensors.torch import save_file

    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    sd = hf_state_dict(model)
    if dtype != torch.float32:
        sd = OrderedDict((k, v.to(dtype)) for k, v in sd.items())
    # safetensors refuses shared storage; hf_state_dict() already stores tied weights once.
    save_file(sd, str(out / "model.safetensors"),
              metadata={"format": "pt", "generated_by": "shennong model/export/to_hf.py"})
    cfg = hf_config_dict(model, Path(tokenizer_dir) if tokenizer_dir else None,
                         dtype=str(dtype).replace("torch.", ""))
    (out / "config.json").write_text(json.dumps(cfg, indent=2, ensure_ascii=False) + "\n",
                                     encoding="utf-8")
    if tokenizer_dir is not None:
        src = Path(tokenizer_dir)
        for name in ("tokenizer.json", "tokenizer_config.json", "special_tokens_map.json"):
            if (src / name).exists():
                shutil.copyfile(src / name, out / name)
    return {"config": cfg, "num_tensors": len(sd), "bytes": (out / "model.safetensors").stat().st_size}


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--checkpoint", required=True, help="training checkpoint .pt")
    ap.add_argument("--tokenizer", default=None, help="dir containing tokenizer.json")
    ap.add_argument("--out", required=True, help="output HF directory")
    ap.add_argument("--dtype", default="f32", choices=["f32", "f16", "bf16"])
    args = ap.parse_args()

    model = load_model(args.checkpoint)
    dt = {"f32": torch.float32, "f16": torch.float16, "bf16": torch.bfloat16}[args.dtype]
    info = write_hf(model, args.out, args.tokenizer, dtype=dt)
    print(f"wrote {args.out}: {info['num_tensors']} tensors, "
          f"{info['bytes']:,} bytes; params={model.num_parameters():,}")
    print(json.dumps(info["config"], indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
