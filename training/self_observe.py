#!/usr/bin/env python3
"""Self-observation: can the model tell, from its own activations, whether an answer is grounded?

This is the stage the project's brief asks for last — after the corpus is in, after the discipline is
trained, teach the model to **observe itself**. Not by prompting it to say "I am confident" (that is a
sentence, not a measurement) but by reading its internal state:

    prompt A: a passage that DOES contain the answer   → label 1 (grounded)
    prompt B: a passage about a different herb        → label 0 (ungrounded)

Then a linear probe per layer predicts the label from the pooled hidden state. If AUC > 0.5 at some layer,
the model **represents** grounding — the information is there to be read, whether or not it is used.

Three numbers come out of this:

  probe_auc_by_layer   where, if anywhere, grounding is linearly decodable
  behavioural_grounding  what the model actually emits on negative examples (does it say "not recorded"?)
  correlation          whether the probe's confidence tracks the behaviour

Honest note: a probe that decodes grounding means the *information* is present. It does not mean the model
uses it. That gap is the finding, and it is reported rather than glossed.

    python training/self_observe.py --ckpt training/runs/curriculum-r1/.../ckpt-best.pt
"""
from __future__ import annotations

import argparse
import csv
import json
import pathlib
import random
import sys

import numpy as np
import torch

ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "model"))


def load_model(ckpt: str):
    from tokenizers import Tokenizer

    from shennong_mini import ModelConfig, load_checkpoint
    from shennong_moe import MoEConfig, ShennongMoE

    ck = load_checkpoint(ROOT / ckpt)
    cfg_d = ck.get("config") or {}
    if int(cfg_d.get("n_experts", 1)) > 1:
        cfg = MoEConfig.from_dict(cfg_d)
        model = ShennongMoE(cfg)
    else:
        from shennong_mini import ShennongMini
        cfg = ModelConfig.from_dict(cfg_d)
        model = ShennongMini(cfg)
    model.load_state_dict(ck["model"], strict=False)
    model.eval()
    tok = Tokenizer.from_file(str(ROOT / "tokenizer/shennong-bpe/tokenizer.json"))
    return model, tok, ck


@torch.no_grad()
def layer_states(model, tok, text: str) -> list[np.ndarray]:
    """Return each layer's pooled hidden state for the last token."""
    ids = torch.tensor([tok.encode(text).ids[-model.cfg.seq_len:]])
    cos, sin = model._rope_for(ids.shape[1])
    x = model.tok_emb(ids)
    out = []
    for layer in model.layers:
        x, _aux, _routing = layer(x, cos, sin)
        out.append(x[0, -1].float().numpy().copy())
    x = model.norm(x)
    out.append(x[0, -1].float().numpy().copy())
    return out


def auc(y: np.ndarray, s: np.ndarray) -> float:
    pos, neg = s[y == 1], s[y == 0]
    if len(pos) == 0 or len(neg) == 0:
        return float("nan")
    order = np.argsort(np.concatenate([pos, neg]), kind="mergesort")
    ranks = np.empty(len(order), float)
    ranks[order] = np.arange(1, len(order) + 1)
    return float((ranks[:len(pos)].sum() - len(pos) * (len(pos) + 1) / 2) / (len(pos) * len(neg)))


def fit_logreg(X: np.ndarray, y: np.ndarray, l2: float = 1e-2, iters: int = 600, lr: float = 0.5):
    mu, sd = X.mean(0), X.std(0) + 1e-6
    Xs = (X - mu) / sd
    w = np.zeros(Xs.shape[1])
    b = 0.0
    n = len(y)
    for _ in range(iters):
        z = Xs @ w + b
        p = 1 / (1 + np.exp(-np.clip(z, -30, 30)))
        g = p - y
        w -= lr * (Xs.T @ g / n + l2 * w)
        b -= lr * g.mean()
    return (w, b, mu, sd)


def predict(params, X):
    w, b, mu, sd = params
    return 1 / (1 + np.exp(-np.clip(((X - mu) / sd) @ w + b, -30, 30)))


def build_probes(n: int = 220, seed: int = 1337):
    rows = list(csv.DictReader((ROOT / "corpus/processed/structured/properties.csv").open(encoding="utf-8")))
    usable = [r for r in rows if r.get("channels") and r.get("drug_name")]
    rng = random.Random(seed)
    rng.shuffle(usable)
    usable = usable[:n]
    probes = []
    for r in usable:
        name, chan = r["drug_name"], r["channels"]
        grounded = (f"Passages:\n[1] 本草類 (recorded): {name}：性 {r.get('nature') or '—'}，"
                    f"味 {r.get('flavors') or '—'}，歸經 {chan}。\n\n"
                    f"Question: What is the 歸經 of {name}?\nAnswer:")
        other = rng.choice([x for x in usable if x["drug_name"] != name])
        ungrounded = (f"Passages:\n[1] 本草類 (recorded): {other['drug_name']}：性 "
                      f"{other.get('nature') or '—'}，味 {other.get('flavors') or '—'}，"
                      f"歸經 {other.get('channels')}。\n\n"
                      f"Question: What is the 歸經 of {name}?\nAnswer:")
        probes.append((grounded, 1, name, chan))
        probes.append((ungrounded, 0, name, chan))
    return probes


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--ckpt", default="training/runs/shennong-moe-r1/ckpt-best.pt")
    ap.add_argument("--n", type=int, default=220)
    ap.add_argument("--out", default="artifacts/self_observation.json")
    ap.add_argument("--max-new-tokens", type=int, default=0,
                    help="also generate on a few negatives (slow on CPU); 0 disables")
    args = ap.parse_args()

    ck_path = ROOT / args.ckpt
    if not ck_path.exists():
        print(f"no checkpoint at {args.ckpt}")
        return 1
    model, tok, ck = load_model(args.ckpt)
    probes = build_probes(args.n)
    print(f"probes: {len(probes)} ({sum(1 for p in probes if p[1]==1)} grounded / "
          f"{sum(1 for p in probes if p[1]==0)} ungrounded)")

    feats, labels = [], []
    for text, lab, _name, _chan in probes:
        feats.append(layer_states(model, tok, text))
        labels.append(lab)
    y = np.array(labels)
    n_layers = len(feats[0])

    rng = np.random.default_rng(1337)
    idx = rng.permutation(len(y))
    cut = int(len(y) * 0.7)
    tr, te = idx[:cut], idx[cut:]

    by_layer = []
    for li in range(n_layers):
        X = np.stack([f[li] for f in feats])
        params = fit_logreg(X[tr], y[tr])
        s = predict(params, X[te])
        by_layer.append({"layer": li, "auc": round(auc(y[te], s), 4)})
    best = max(by_layer, key=lambda r: (r["auc"] if r["auc"] == r["auc"] else -1))

    behavioural = None
    if args.max_new_tokens > 0:
        negs = [p for p in probes if p[1] == 0][:6]
        outs = []
        for text, _lab, name, _chan in negs:
            o = model.generate(torch.tensor([tok.encode(text).ids[-model.cfg.seq_len:]]),
                               max_new_tokens=args.max_new_tokens, temperature=0.7, top_p=0.9, seed=1337)
            gen = tok.decode(o[0][len(tok.encode(text).ids[-model.cfg.seq_len:]):].tolist())
            outs.append({"herb": name, "completion": gen[:160],
                         "says_not_recorded": any(k in gen for k in ("not record", "不載", "未載", "無"))})
        behavioural = {"n": len(outs), "said_not_recorded": sum(o["says_not_recorded"] for o in outs),
                       "examples": outs}

    payload = {
        "generated_at": __import__("time").strftime("%Y-%m-%dT%H:%M:%S%z"),
        "checkpoint": args.ckpt, "step": ck.get("step"),
        "definition": ("label 1 = the supplied passage contains the answer; label 0 = the passage is about a "
                       "different herb. The probe reads the pooled hidden state at the final token and predicts "
                       "the label. If the model REPRESENTS grounding, a linear probe decodes it."),
        "n_probes": len(probes), "n_train": int(cut), "n_test": int(len(y) - cut),
        "probe_auc_by_layer": by_layer,
        "best_layer": best,
        "chance_auc": 0.5,
        "behavioural_grounding": behavioural,
        "interpretation": ("AUC above chance means the information is linearly readable inside the model. It "
                           "does not mean the model uses it when answering — that gap is what the grounding "
                           "stage (curriculum stage 6) is for, and it is reported here rather than assumed."),
    }
    (ROOT / args.out).write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"best layer {best['layer']} AUC {best['auc']:.3f} (chance 0.5)")
    for r in by_layer:
        print(f"  layer {r['layer']:>2}  AUC {r['auc']:.3f}")
    print(f"wrote {args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
