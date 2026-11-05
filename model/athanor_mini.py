"""ATHANOR-Mini: a small Llama-style decoder for computational ethnopharmacology.

Written from scratch in plain PyTorch (no transformers/ xformers / flash-attn) so the
whole training stack is reproducible on a CPU-only machine.  Architecture matches
Llama 2/3 and Qwen2.5 (RMSNorm, RoPE, SwiGLU, grouped-query attention, tied
embeddings), so the *same* file can instantiate the from-scratch ``athanor-mini``
and a Qwen2.5-0.5B-shaped ``athanor-0.5B`` config.

Reference: Touvron et al. 2023 (Llama 2, arXiv:2307.09288); Su et al. 2021 (RoPE,
arXiv:2104.09864); Shazeer 2020 (SwiGLU, arXiv:2002.05202).

This model is a research artefact for hypothesis drafting.  It is *not* a medical
device and must not be used for diagnosis, dosing or treatment decisions.
"""

from __future__ import annotations

import json
import math
from dataclasses import dataclass, asdict, field
from pathlib import Path

import torch
import torch.nn as nn
import torch.nn.functional as F


# --------------------------------------------------------------------------------------
# Config
# --------------------------------------------------------------------------------------
@dataclass
class ModelConfig:
    """Hyper-parameters of the decoder.  Mirrors the `config.json` fields used by HF."""

    vocab_size: int = 16384
    d_model: int = 384
    n_layer: int = 8
    n_head: int = 6
    n_kv_head: int = 2
    d_ff: int = 1024
    seq_len: int = 512
    rope_theta: float = 10000.0
    norm_eps: float = 1e-5
    tie_word_embeddings: bool = True
    init_std: float = 0.02
    attention_bias: bool = False

    def __post_init__(self) -> None:
        if self.d_model % self.n_head != 0:
            raise ValueError("d_model must be divisible by n_head")
        if self.n_head % self.n_kv_head != 0:
            raise ValueError("n_head must be divisible by n_kv_head")
        if self.d_model % 2 != 0:
            raise ValueError("d_model must be even (RoPE pairs the head dim)")

    @property
    def head_dim(self) -> int:
        return self.d_model // self.n_head

    @property
    def n_head_per_kv(self) -> int:
        return self.n_head // self.n_kv_head

    @classmethod
    def from_json(cls, path: str | Path) -> "ModelConfig":
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        return cls.from_dict(data)

    @classmethod
    def from_dict(cls, data: dict) -> "ModelConfig":
        # Accept both native names and HF-ish aliases (hidden_size, num_hidden_layers...).
        aliases = {
            "hidden_size": "d_model",
            "intermediate_size": "d_ff",
            "num_hidden_layers": "n_layer",
            "num_attention_heads": "n_head",
            "num_key_value_heads": "n_kv_head",
            "max_position_embeddings": "seq_len",
            "rms_norm_eps": "norm_eps",
        }
        clean = {}
        for key, value in data.items():
            key = aliases.get(key, key)
            if key in cls.__dataclass_fields__:
                clean[key] = value
        return cls(**clean)

    def to_dict(self) -> dict:
        return asdict(self)

    @property
    def n_params_estimate(self) -> int:
        """Parameter count without building the module (tied embeddings counted once)."""
        emb = self.vocab_size * self.d_model
        q = self.d_model * self.n_head * self.head_dim
        k = self.d_model * self.n_kv_head * self.head_dim
        v = self.d_model * self.n_kv_head * self.head_dim
        o = self.n_head * self.head_dim * self.d_model
        attn = q + k + v + o + (3 * self.d_model if self.attention_bias else 0)
        mlp = 3 * self.d_model * self.d_ff
        norms = 2 * self.d_model
        return emb + self.n_layer * (attn + mlp + norms) + self.d_model  # + final norm


# --------------------------------------------------------------------------------------
# Building blocks
# --------------------------------------------------------------------------------------
class RMSNorm(nn.Module):
    """Root-mean-square layer norm (Zhang & Sennrich 2019, arXiv:1910.07467)."""

    def __init__(self, dim: int, eps: float = 1e-5) -> None:
        super().__init__()
        self.eps = eps
        self.weight = nn.Parameter(torch.ones(dim))

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        dtype = x.dtype
        x = x.float()
        x = x * torch.rsqrt(x.pow(2).mean(-1, keepdim=True) + self.eps)
        return (x.to(dtype)) * self.weight


def precompute_rope(dim: int, max_seq_len: int, theta: float) -> tuple[torch.Tensor, torch.Tensor]:
    """cos/sin tables of shape (max_seq_len, dim) for rotary position embeddings."""
    inv_freq = 1.0 / (theta ** (torch.arange(0, dim, 2, dtype=torch.float32) / dim))
    pos = torch.arange(max_seq_len, dtype=torch.float32)
    freqs = torch.outer(pos, inv_freq)          # (T, dim/2)
    emb = torch.cat((freqs, freqs), dim=-1)     # (T, dim)
    return emb.cos(), emb.sin()


def rotate_half(x: torch.Tensor) -> torch.Tensor:
    half = x.shape[-1] // 2
    return torch.cat((-x[..., half:], x[..., :half]), dim=-1)


def apply_rope(x: torch.Tensor, cos: torch.Tensor, sin: torch.Tensor) -> torch.Tensor:
    # x: (B, H, T, head_dim); cos/sin: (T, head_dim)
    cos = cos[None, None, :, :].to(x.dtype)
    sin = sin[None, None, :, :].to(x.dtype)
    return x * cos + rotate_half(x) * sin


class Attention(nn.Module):
    """Causal multi-head / grouped-query attention."""

    def __init__(self, cfg: ModelConfig) -> None:
        super().__init__()
        self.n_head = cfg.n_head
        self.n_kv_head = cfg.n_kv_head
        self.n_head_per_kv = cfg.n_head_per_kv
        self.head_dim = cfg.head_dim
        bias = cfg.attention_bias
        self.q_proj = nn.Linear(cfg.d_model, cfg.n_head * self.head_dim, bias=bias)
        self.k_proj = nn.Linear(cfg.d_model, cfg.n_kv_head * self.head_dim, bias=bias)
        self.v_proj = nn.Linear(cfg.d_model, cfg.n_kv_head * self.head_dim, bias=bias)
        self.o_proj = nn.Linear(cfg.n_head * self.head_dim, cfg.d_model, bias=bias)

    def forward(self, x: torch.Tensor, cos: torch.Tensor, sin: torch.Tensor) -> torch.Tensor:
        b, t, _ = x.shape
        q = self.q_proj(x).view(b, t, self.n_head, self.head_dim).transpose(1, 2)
        k = self.k_proj(x).view(b, t, self.n_kv_head, self.head_dim).transpose(1, 2)
        v = self.v_proj(x).view(b, t, self.n_kv_head, self.head_dim).transpose(1, 2)
        q = apply_rope(q, cos, sin)
        k = apply_rope(k, cos, sin)
        if self.n_head_per_kv > 1:  # broadcast KV heads across query groups
            k = k.repeat_interleave(self.n_head_per_kv, dim=1)
            v = v.repeat_interleave(self.n_head_per_kv, dim=1)
        out = F.scaled_dot_product_attention(q, k, v, is_causal=t > 1)
        out = out.transpose(1, 2).contiguous().view(b, t, -1)
        return self.o_proj(out)


class MLP(nn.Module):
    """SwiGLU feed-forward (Shazeer 2020)."""

    def __init__(self, cfg: ModelConfig) -> None:
        super().__init__()
        self.gate_proj = nn.Linear(cfg.d_model, cfg.d_ff, bias=False)
        self.up_proj = nn.Linear(cfg.d_model, cfg.d_ff, bias=False)
        self.down_proj = nn.Linear(cfg.d_ff, cfg.d_model, bias=False)

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        return self.down_proj(F.silu(self.gate_proj(x)) * self.up_proj(x))


class Block(nn.Module):
    """Pre-norm Llama decoder block."""

    def __init__(self, cfg: ModelConfig) -> None:
        super().__init__()
        self.attn_norm = RMSNorm(cfg.d_model, cfg.norm_eps)
        self.attn = Attention(cfg)
        self.mlp_norm = RMSNorm(cfg.d_model, cfg.norm_eps)
        self.mlp = MLP(cfg)

    def forward(self, x: torch.Tensor, cos: torch.Tensor, sin: torch.Tensor) -> torch.Tensor:
        x = x + self.attn(self.attn_norm(x), cos, sin)
        x = x + self.mlp(self.mlp_norm(x))
        return x


# --------------------------------------------------------------------------------------
# Model
# --------------------------------------------------------------------------------------
class AthanorMini(nn.Module):
    """Small Llama-style causal language model."""

    def __init__(self, cfg: ModelConfig) -> None:
        super().__init__()
        self.cfg = cfg
        self.tok_emb = nn.Embedding(cfg.vocab_size, cfg.d_model)
        self.layers = nn.ModuleList([Block(cfg) for _ in range(cfg.n_layer)])
        self.norm = RMSNorm(cfg.d_model, cfg.norm_eps)
        self.lm_head = nn.Linear(cfg.d_model, cfg.vocab_size, bias=False)
        if cfg.tie_word_embeddings:
            self.lm_head.weight = self.tok_emb.weight
        cos, sin = precompute_rope(cfg.head_dim, cfg.seq_len, cfg.rope_theta)
        self.register_buffer("rope_cos", cos, persistent=False)
        self.register_buffer("rope_sin", sin, persistent=False)
        self.apply(self._init_weights)
        # Scaled init for the residual path (GPT-2 style) keeps logits sane at depth.
        for name, p in self.named_parameters():
            if name.endswith("o_proj.weight") or name.endswith("down_proj.weight"):
                nn.init.normal_(p, mean=0.0, std=cfg.init_std / math.sqrt(2 * cfg.n_layer))
        self.gradient_checkpointing = False

    def _init_weights(self, module: nn.Module) -> None:
        if isinstance(module, nn.Linear):
            nn.init.normal_(module.weight, mean=0.0, std=self.cfg.init_std)
            if module.bias is not None:
                nn.init.zeros_(module.bias)
        elif isinstance(module, nn.Embedding):
            nn.init.normal_(module.weight, mean=0.0, std=self.cfg.init_std)

    # -- convenience ------------------------------------------------------------------
    @classmethod
    def from_config(cls, config: ModelConfig | str | Path | dict) -> "AthanorMini":
        if isinstance(config, (str, Path)):
            config = ModelConfig.from_json(config)
        elif isinstance(config, dict):
            config = ModelConfig.from_dict(config)
        return cls(config)

    def num_parameters(self, non_embedding: bool = False) -> int:
        n = sum(p.numel() for p in self.parameters())
        if non_embedding:
            n -= self.tok_emb.weight.numel()
        return n

    def _rope_for(self, t: int) -> tuple[torch.Tensor, torch.Tensor]:
        if t <= self.rope_cos.shape[0]:
            return self.rope_cos[:t], self.rope_sin[:t]
        # Sequence longer than the configured window: recompute on the fly.
        cos, sin = precompute_rope(self.cfg.head_dim, t, self.cfg.rope_theta)
        return cos.to(self.rope_cos.device), sin.to(self.rope_cos.device)

    # -- forward ----------------------------------------------------------------------
    def forward(
        self,
        input_ids: torch.Tensor,
        targets: torch.Tensor | None = None,
        ignore_index: int = -100,
    ) -> tuple[torch.Tensor, torch.Tensor | None]:
        b, t = input_ids.shape
        cos, sin = self._rope_for(t)
        x = self.tok_emb(input_ids)
        for layer in self.layers:
            x = layer(x, cos, sin)
        x = self.norm(x)
        logits = self.lm_head(x)
        loss = None
        if targets is not None:
            loss = F.cross_entropy(
                logits.view(-1, logits.size(-1)), targets.reshape(-1), ignore_index=ignore_index
            )
        return logits, loss

    # -- generation -------------------------------------------------------------------
    @torch.no_grad()
    def generate(
        self,
        input_ids: torch.Tensor,
        max_new_tokens: int = 128,
        temperature: float = 0.8,
        top_k: int | None = 50,
        top_p: float | None = 0.95,
        repetition_penalty: float = 1.0,
        eos_token_id: int | None = None,
        seed: int | None = None,
    ) -> torch.Tensor:
        """Autoregressive sampling with temperature / top-k / top-p / repetition penalty.

        ``input_ids`` is (B, T) and must be non-empty.  Returns (B, T + new_tokens).
        """
        self.eval()
        device = next(self.parameters()).device
        input_ids = input_ids.to(device)
        generator = None
        if seed is not None:
            generator = torch.Generator(device="cpu").manual_seed(seed)
        for _ in range(max_new_tokens):
            idx = input_ids[:, -self.cfg.seq_len:]
            logits, _ = self(idx)
            logits = logits[:, -1, :].float()

            if repetition_penalty != 1.0:
                for row in range(input_ids.shape[0]):
                    seen = torch.unique(input_ids[row])
                    vals = logits[row, seen]
                    logits[row, seen] = torch.where(
                        vals > 0, vals / repetition_penalty, vals * repetition_penalty
                    )

            logits = logits / max(temperature, 1e-6)
            if top_k is not None and top_k > 0:
                k = min(top_k, logits.size(-1))
                kth = torch.topk(logits, k, dim=-1).values[:, -1:]
                logits = torch.where(logits < kth, torch.full_like(logits, float("-inf")), logits)
            if top_p is not None and 0.0 < top_p < 1.0:
                sorted_logits, sorted_idx = torch.sort(logits, descending=True, dim=-1)
                probs = F.softmax(sorted_logits, dim=-1)
                cumulative = torch.cumsum(probs, dim=-1)
                mask = cumulative - probs > top_p
                sorted_logits = sorted_logits.masked_fill(mask, float("-inf"))
                logits = torch.full_like(logits, float("-inf")).scatter(1, sorted_idx, sorted_logits)

            probs = F.softmax(logits, dim=-1)
            next_token = torch.multinomial(probs, num_samples=1, generator=generator)
            input_ids = torch.cat([input_ids, next_token], dim=1)
            if eos_token_id is not None and (next_token == eos_token_id).all():
                break
        return input_ids


# --------------------------------------------------------------------------------------
# Checkpoint helpers (shared by training scripts)
# --------------------------------------------------------------------------------------
def save_checkpoint(path: str | Path, model: AthanorMini, optimizer=None, step: int = 0,
                    extra: dict | None = None) -> None:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "model": model.state_dict(),
        "config": model.cfg.to_dict(),
        "step": step,
        "optimizer": optimizer.state_dict() if optimizer is not None else None,
        "extra": extra or {},
    }
    tmp = path.with_suffix(path.suffix + ".tmp")
    torch.save(payload, tmp)
    tmp.replace(path)  # atomic-ish: never leave a half-written checkpoint


def load_checkpoint(path: str | Path, map_location: str | torch.device = "cpu") -> dict:
    return torch.load(path, map_location=map_location)


if __name__ == "__main__":  # tiny smoke test
    for name in ("mini", "flagship-0.5b"):
        path = Path(__file__).parent / "configs" / f"{name}.json"
        if path.exists():
            cfg = ModelConfig.from_json(path)
            m = AthanorMini(cfg)
            print(f"{name}: {cfg}")
            print(f"  params={m.num_parameters():,}  non-emb={m.num_parameters(True):,}  "
                  f"estimate={cfg.n_params_estimate:,}")
