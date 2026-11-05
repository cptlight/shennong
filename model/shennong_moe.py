#!/usr/bin/env python3
"""SHENNONG-MoE — a sparse mixture-of-experts decoder over the same corpus and tokenizer.

Motivation (and the honest caveat)
----------------------------------
A dense 8.7 M model is capacity-limited: every token activates every parameter, so the FFN has to
serve Classical Chinese, Latin, English and Devanagari pharmaceuticals at once. A sparse MoE keeps the
**parameters** (capacity) but spends only `top_k / n_experts` of the FFN **compute** per token, so at
equal FLOPs it can hold more knowledge. That is the reason to try it.

The caveat we will measure rather than assume: at this scale (≈19 M total) and on a laptop CPU, the
routing overhead is a large fraction of the step cost, so MoE may be *slower per token* than dense. The
comparison is reported honestly in `training/runs/moe-vs-dense.json`; if MoE loses, we say so.

The interesting scientific question it enables: **does the router independently rediscover the
tradition/script structure of the corpus?** If tokens from 本草綱目 concentrate on a different expert
than English foundational-science tokens, the routing is not just a compute trick — it is evidence
that the domains are separable in representation space. `expert_language_report()` measures that.

Architecture
------------
Same trunk as the dense model (RMSNorm · RoPE · GQA · SwiGLU), except each block's FFN becomes
`n_experts` SwiGLU experts with a linear top-k router. Dispatch is a deterministic masked loop over
experts (no custom kernels — correct and portable, and fast enough at 4 experts on CPU).

    python model/shennong_moe.py                       # parameter accounting
"""
from __future__ import annotations

import json
import sys
from dataclasses import asdict, dataclass
from pathlib import Path

import torch
import torch.nn as nn
import torch.nn.functional as F

sys.path.insert(0, str(Path(__file__).resolve().parent))

from shennong_mini import Attention, RMSNorm, precompute_rope, save_checkpoint, load_checkpoint  # noqa: E402


# --------------------------------------------------------------------------------------
# Config
# --------------------------------------------------------------------------------------
@dataclass
class MoEConfig:
    """Decoder + MoE hyper-parameters. Mirrors HF-ish names where they exist."""

    vocab_size: int = 16384
    d_model: int = 256
    n_layer: int = 6
    n_head: int = 4
    n_kv_head: int = 1
    d_ff: int = 768
    seq_len: int = 512
    rope_theta: float = 10000.0
    norm_eps: float = 1e-5
    tie_word_embeddings: bool = True
    init_std: float = 0.02
    attention_bias: bool = False
    # --- MoE ---
    n_experts: int = 4
    top_k: int = 2
    aux_loss_coef: float = 0.01
    router_jitter: float = 0.01
    expert_dropout: float = 0.0

    def __post_init__(self) -> None:
        if self.d_model % self.n_head != 0:
            raise ValueError("d_model must be divisible by n_head")
        if self.n_head % self.n_kv_head != 0:
            raise ValueError("n_head must be divisible by n_kv_head")
        if self.d_model % 2 != 0:
            raise ValueError("d_model must be even (RoPE pairs the head dim)")
        if not 1 <= self.top_k <= self.n_experts:
            raise ValueError("require 1 <= top_k <= n_experts")

    @property
    def head_dim(self) -> int:
        return self.d_model // self.n_head

    @property
    def n_head_per_kv(self) -> int:
        return self.n_head // self.n_kv_head

    @classmethod
    def from_json(cls, path: str | Path) -> "MoEConfig":
        return cls.from_dict(json.loads(Path(path).read_text(encoding="utf-8")))

    @classmethod
    def from_dict(cls, data: dict) -> "MoEConfig":
        aliases = {"hidden_size": "d_model", "intermediate_size": "d_ff",
                   "num_hidden_layers": "n_layer", "num_attention_heads": "n_head",
                   "num_key_value_heads": "n_kv_head", "max_position_embeddings": "seq_len",
                   "rms_norm_eps": "norm_eps", "num_experts": "n_experts",
                   "num_experts_per_tok": "top_k"}
        clean = {}
        for k, v in data.items():
            k = aliases.get(k, k)
            if k in cls.__dataclass_fields__:
                clean[k] = v
        return cls(**clean)

    def to_dict(self) -> dict:
        return asdict(self)

    # -- parameter accounting: total (capacity) and active (per-token compute) -----------
    def _attn_params(self) -> int:
        q = self.d_model * self.n_head * self.head_dim
        k = self.d_model * self.n_kv_head * self.head_dim
        v = self.d_model * self.n_kv_head * self.head_dim
        o = self.n_head * self.head_dim * self.d_model
        return q + k + v + o + (3 * self.d_model if self.attention_bias else 0)

    def _expert_params(self) -> int:
        return 3 * self.d_model * self.d_ff

    @property
    def n_params_estimate(self) -> int:
        emb = self.vocab_size * self.d_model
        router = self.d_model * self.n_experts + self.n_experts
        per_layer = self._attn_params() + self.n_experts * self._expert_params() + router + 2 * self.d_model
        return emb + self.n_layer * per_layer + self.d_model

    @property
    def n_params_active(self) -> int:
        emb = self.vocab_size * self.d_model
        router = self.d_model * self.n_experts + self.n_experts
        per_layer = (self._attn_params() + self.top_k * self._expert_params()
                     + router + 2 * self.d_model)
        return emb + self.n_layer * per_layer + self.d_model


# --------------------------------------------------------------------------------------
# MoE FFN
# --------------------------------------------------------------------------------------
class SwiGLUExpert(nn.Module):
    def __init__(self, cfg: MoEConfig) -> None:
        super().__init__()
        self.gate_proj = nn.Linear(cfg.d_model, cfg.d_ff, bias=False)
        self.up_proj = nn.Linear(cfg.d_model, cfg.d_ff, bias=False)
        self.down_proj = nn.Linear(cfg.d_ff, cfg.d_model, bias=False)

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        return self.down_proj(F.silu(self.gate_proj(x)) * self.up_proj(x))


class MoEFFN(nn.Module):
    """Top-k noisy-gated mixture of SwiGLU experts with Switch-style load balancing.

    returns (output, aux_loss, routing) where routing is (n_tokens, n_experts) top-k weights — kept so
    the training loop can log expert usage and the diagnostic can measure expert↔language association.
    """

    def __init__(self, cfg: MoEConfig) -> None:
        super().__init__()
        self.cfg = cfg
        self.router = nn.Linear(cfg.d_model, cfg.n_experts, bias=True)
        self.experts = nn.ModuleList([SwiGLUExpert(cfg) for _ in range(cfg.n_experts)])

    def forward(self, x: torch.Tensor):
        b, t, d = x.shape
        flat = x.reshape(-1, d)                       # (N, d)

        logits = self.router(flat).float()            # (N, E)
        if self.training and self.cfg.router_jitter > 0:
            # noisy top-k gating (Shazeer et al. 2017): exploration early, deterministic at eval
            logits = logits + torch.randn_like(logits) * self.cfg.router_jitter

        probs = F.softmax(logits, dim=-1)             # (N, E)
        top_w, top_i = torch.topk(probs, self.cfg.top_k, dim=-1)
        top_w = top_w / top_w.sum(dim=-1, keepdim=True)   # renormalise gate weights

        out = torch.zeros_like(flat)
        # deterministic masked dispatch: one gather per expert, no scatter kernels
        for e in range(self.cfg.n_experts):
            hit = (top_i == e)                        # (N, top_k) bool
            if not bool(hit.any()):
                continue
            rows = hit.any(dim=-1)                    # (N,)
            # gate weight for this expert per token (0 where not selected)
            w = (top_w * hit.float()).sum(dim=-1)[rows].unsqueeze(-1)   # (n_rows, 1)
            out[rows] += self.experts[e](flat[rows]) * w

        # Switch-style load balance: E * sum_i(f_i * p_i); penalises collapsed routing.
        with torch.no_grad():
            mask = F.one_hot(top_i, self.cfg.n_experts).float().sum(dim=1)   # (N, E)
            f = mask.mean(dim=0)                      # fraction of tokens per expert
        p = probs.mean(dim=0)
        aux = self.cfg.n_experts * torch.sum(f * p)

        routing = torch.zeros_like(probs).scatter(1, top_i, top_w)
        return out.reshape(b, t, d), aux, routing


# --------------------------------------------------------------------------------------
# Block / model
# --------------------------------------------------------------------------------------
class MoEBlock(nn.Module):
    def __init__(self, cfg: MoEConfig) -> None:
        super().__init__()
        self.attn_norm = RMSNorm(cfg.d_model, cfg.norm_eps)
        self.attn = Attention(cfg)
        self.mlp_norm = RMSNorm(cfg.d_model, cfg.norm_eps)
        self.moe = MoEFFN(cfg)

    def forward(self, x, cos, sin):
        x = x + self.attn(self.attn_norm(x), cos, sin)
        h, aux, routing = self.moe(self.mlp_norm(x))
        return x + h, aux, routing


class ShennongMoE(nn.Module):
    def __init__(self, cfg: MoEConfig) -> None:
        super().__init__()
        self.cfg = cfg
        self.tok_emb = nn.Embedding(cfg.vocab_size, cfg.d_model)
        self.layers = nn.ModuleList([MoEBlock(cfg) for _ in range(cfg.n_layer)])
        self.norm = RMSNorm(cfg.d_model, cfg.norm_eps)
        self.lm_head = nn.Linear(cfg.d_model, cfg.vocab_size, bias=False)
        if cfg.tie_word_embeddings:
            self.lm_head.weight = self.tok_emb.weight
        self.apply(self._init)
        cos, sin = precompute_rope(cfg.d_model // cfg.n_head, cfg.seq_len, cfg.rope_theta)
        self.register_buffer("rope_cos", cos, persistent=False)
        self.register_buffer("rope_sin", sin, persistent=False)
        # diagnostics filled on each forward
        self.last_aux_loss: float | None = None
        self.last_ce_loss: float | None = None
        self.last_routing: torch.Tensor | None = None

    def _init(self, m: nn.Module) -> None:
        if isinstance(m, nn.Linear):
            nn.init.normal_(m.weight, mean=0.0, std=self.cfg.init_std)
            if m.bias is not None:
                nn.init.zeros_(m.bias)
        elif isinstance(m, nn.Embedding):
            nn.init.normal_(m.weight, mean=0.0, std=self.cfg.init_std)

    @classmethod
    def from_config(cls, cfg) -> "ShennongMoE":
        return cls(cfg)

    def num_parameters(self, non_embedding: bool = False) -> int:
        n = sum(p.numel() for p in self.parameters())
        return n - self.tok_emb.weight.numel() if non_embedding else n

    def num_active_parameters(self) -> int:
        return self.cfg.n_params_active

    def _rope_for(self, t: int):
        if t <= self.rope_cos.shape[0]:
            return self.rope_cos[:t], self.rope_sin[:t]
        cos, sin = precompute_rope(self.cfg.n_head and self.cfg.head_dim, t, self.cfg.rope_theta)
        return cos.to(self.rope_cos.device), sin.to(self.rope_cos.device)

    def forward(self, input_ids: torch.Tensor, targets: torch.Tensor | None = None,
                ignore_index: int = -100):
        b, t = input_ids.shape
        cos, sin = self._rope_for(t)
        x = self.tok_emb(input_ids)
        aux_total = torch.zeros((), device=x.device)
        routing_last = None
        for layer in self.layers:
            x, aux, routing = layer(x, cos, sin)
            aux_total = aux_total + aux
            routing_last = routing
        x = self.norm(x)
        logits = self.lm_head(x)
        self.last_aux_loss = float(aux_total) / max(1, len(self.layers))
        self.last_routing = routing_last
        if targets is None:
            self.last_ce_loss = None
            return logits, None
        ce = F.cross_entropy(logits.view(-1, logits.size(-1)), targets.reshape(-1),
                             ignore_index=ignore_index)
        self.last_ce_loss = float(ce)
        loss = ce + self.cfg.aux_loss_coef * self.last_aux_loss
        return logits, loss

    @torch.no_grad()
    def generate(self, input_ids, max_new_tokens=128, temperature=0.8, top_k=None,
                 top_p=0.95, repetition_penalty=1.0, eos_token_id=None, seed=None):
        self.eval()
        if seed is not None:
            torch.manual_seed(seed)
        ids = input_ids
        for _ in range(max_new_tokens):
            ctx = ids[:, -self.cfg.seq_len:]
            logits, _ = self.forward(ctx)
            logits = logits[:, -1, :].float() / max(temperature, 1e-6)
            if repetition_penalty != 1.0:
                for row in range(ids.shape[0]):
                    seen = set(ids[row].tolist())
                    logits[row, list(seen)] /= repetition_penalty
            if top_k:
                v, _ = torch.topk(logits, min(top_k, logits.size(-1)))
                logits[logits < v[:, [-1]]] = -float("inf")
            probs = F.softmax(logits, dim=-1)
            nxt = torch.multinomial(probs, 1)
            ids = torch.cat([ids, nxt], dim=1)
            if eos_token_id is not None and bool((ids[:, -1] == eos_token_id).all()):
                break
        return ids


# --------------------------------------------------------------------------------------
# The scientific diagnostic: does routing recover the tradition/script structure?
# --------------------------------------------------------------------------------------
@torch.no_grad()
def expert_language_report(model: ShennongMoE, tokenizer, texts_by_lang: dict[str, list[str]],
                           max_per_lang: int = 12) -> dict:
    """For each language, which experts do its tokens route to, and is the distribution distinct?

    Returns per-language normalised expert-usage share plus, for each pair of languages, the
    Jensen–Shannon distance between their routing distributions. JS distance near 1 ⇒ the router
    separates those languages; near 0 ⇒ it does not.
    """
    model.eval()
    e = model.cfg.n_experts
    usage: dict[str, torch.Tensor] = {}
    for lang, texts in texts_by_lang.items():
        acc = torch.zeros(e)
        n = 0
        for text in texts[:max_per_lang]:
            enc = tokenizer.encode(text)
            ids = enc.ids[: model.cfg.seq_len]
            if len(ids) < 8:
                continue
            x = torch.tensor([ids])
            # forward through layers, capture mean routing at the last MoE layer
            cos, sin = model._rope_for(len(ids))
            h = model.tok_emb(x)
            for layer in model.layers:
                h2, _, routing = layer(h, cos, sin)
                h = h2
            if routing is None:
                continue
            acc += routing.mean(dim=0)          # mean gate weight per expert
            n += 1
        if n:
            usage[lang] = acc / n

    def js(p: torch.Tensor, q: torch.Tensor) -> float:
        p = p / p.sum()
        q = q / q.sum()
        m = 0.5 * (p + q)
        def kl(a, b):
            return float(torch.sum(a * (torch.log(a + 1e-12) - torch.log(b + 1e-12))))
        return (0.5 * kl(p, m) + 0.5 * kl(q, m)) ** 0.5   # JS *distance*

    pairs = {}
    langs = sorted(usage)
    for i, a in enumerate(langs):
        for b in langs[i + 1:]:
            pairs[f"{a}|{b}"] = round(js(usage[a], usage[b]), 4)

    return {
        "n_experts": e,
        "top_k": model.cfg.top_k,
        "usage_share": {k: [round(float(x), 4) for x in v] for k, v in usage.items()},
        "pairwise_js_distance": pairs,
        "max_pair_js": max(pairs.values()) if pairs else None,
        "note": "JS distance in [0,1]; 0 = identical routing distribution, 1 = disjoint experts.",
    }


if __name__ == "__main__":
    dense = MoEConfig(n_experts=1, top_k=1)
    moe = MoEConfig()
    print(f"dense-equivalent (n_experts=1, top_k=1): {dense.n_params_estimate:,} params")
    print(f"MoE  n_experts={moe.n_experts} top_k={moe.top_k}: "
          f"{moe.n_params_estimate:,} total params, {moe.n_params_active:,} active per token")
    m = ShennongMoE(moe)
    print(f"built: {m.num_parameters():,} params ({m.num_parameters():,} counted), "
          f"active {m.num_active_parameters():,}")
    x = torch.randint(0, moe.vocab_size, (2, 64))
    y = torch.randint(0, moe.vocab_size, (2, 64))
    logits, loss = m(x, y)
    print(f"forward ok: logits {tuple(logits.shape)} loss {float(loss):.4f} "
          f"(ce {m.last_ce_loss:.4f} + aux*{moe.aux_loss_coef} {m.last_aux_loss:.4f})")
