#!/usr/bin/env python3
"""Make an upcycled Qwen2MoE GGUF loadable by llama.cpp 0.3.x.

Two problems, both local to the GGUF, neither affecting the trained weights:

1. `output.weight` is absent because the HF model ties the LM head to the token embedding. llama.cpp's
   qwen2moe loader requires it (the dense qwen2 loader does not, which is why the 0.5B GGUF loads).
   Fix: copy token_embd into output.weight — identical maths for a tied model.

2. The shared expert was built 0-width, then given a 4-wide placeholder to dodge a zero-tensor crash during
   quantization. The 0.3.x loader expects the FULL width (feed_forward_length, 4864) and rejects the
   placeholder. Fix: emit full-width zero tensors. A zero down_proj makes shared_expert(x) = 0, which is what
   the 0-width module produced, so the model is numerically unchanged.

    python scripts/fix_moe_gguf.py --src in.gguf --out out.gguf [--qtype q8_0]
"""
from __future__ import annotations

import argparse
import pathlib
import sys

import numpy as np


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--src", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--width", type=int, default=None, help="shared-expert width (default: feed_forward_length)")
    args = ap.parse_args()

    from gguf import GGMLQuantizationType, GGUFReader, GGUFValueType, GGUFWriter
    from gguf.quants import quantize

    r = GGUFReader(args.src)

    def field_val(name, default=None):
        f = r.fields.get(name)
        if f is None:
            return default
        c = f.contents()
        return c[0] if isinstance(c, (list, tuple)) else c

    arch = field_val("general.architecture")
    if isinstance(arch, bytes):
        arch = arch.decode()
    n_embd = int(field_val(f"{arch}.embedding_length"))
    width = args.width or int(field_val(f"{arch}.feed_forward_length"))
    n_layers = int(field_val(f"{arch}.block_count"))
    print(f"arch={arch} n_embd={n_embd} width={width} layers={n_layers} tensors={len(r.tensors)}")

    have_output = any(t.name == "output.weight" for t in r.tensors)
    SKIP = ("ffn_gate_shexp.weight", "ffn_up_shexp.weight", "ffn_down_shexp.weight")
    shexp = [t.name for t in r.tensors if t.name.endswith(SKIP)]
    print(f"existing: output.weight={have_output}, shexp tensors={len(shexp)}")

    w = GGUFWriter(args.out, arch=arch)
    for name, field in r.fields.items():
        if name == "general.architecture":
            continue
        vtype = field.types[0]
        try:
            c = field.contents()
            if name == "general.file_type":
                w.add_file_type(int(c[0] if isinstance(c, (list, tuple)) else c))
            elif name == "general.quantization_version":
                w.add_quantization_version(int(c[0] if isinstance(c, (list, tuple)) else c))
            elif vtype == GGUFValueType.ARRAY:
                w.add_key_value(name, list(c), vtype, sub_type=field.types[-1])
            else:
                w.add_key_value(name, c[0] if isinstance(c, (list, tuple)) else c, vtype)
        except Exception as exc:  # noqa: BLE001
            print(f"  !! field {name}: {exc}")

    # copy every tensor except the narrow shexp placeholders
    skipped = 0
    for t in r.tensors:
        if t.name.endswith(SKIP):
            skipped += 1
            continue
        w.add_tensor(t.name, t.data, raw_shape=t.data.shape, raw_dtype=t.tensor_type)

    # full-width zero shared experts (q8_0: zeros are exact, ~4.6 MB each)
    # GGUF stores logical shapes reversed: zeros((width, n_embd)) is written as [n_embd, width]
    zq = quantize(np.zeros((width, n_embd), dtype=np.float32), GGMLQuantizationType.Q4_0)      # gate/up
    zq_dn = quantize(np.zeros((n_embd, width), dtype=np.float32), GGMLQuantizationType.Q4_0)   # down
    for i in range(n_layers):
        w.add_tensor(f"blk.{i}.ffn_gate_shexp.weight", zq, raw_shape=zq.shape, raw_dtype=GGMLQuantizationType.Q4_0)
        w.add_tensor(f"blk.{i}.ffn_up_shexp.weight",   zq, raw_shape=zq.shape, raw_dtype=GGMLQuantizationType.Q4_0)
        w.add_tensor(f"blk.{i}.ffn_down_shexp.weight", zq_dn, raw_shape=zq_dn.shape, raw_dtype=GGMLQuantizationType.Q4_0)

    if not have_output:
        emb = next(t for t in r.tensors if t.name == "token_embd.weight")
        w.add_tensor("output.weight", emb.data, raw_shape=emb.data.shape, raw_dtype=emb.tensor_type)

    print(f"skipped {skipped} narrow shexp tensors, added {n_layers*3} full-width zeros"
          f"{'' if have_output else ' + output.weight'}")
    w.write_header_to_file()
    w.write_kv_data_to_file()
    w.write_tensors_to_file()
    w.close()
    out = pathlib.Path(args.out)
    print(f"wrote {out} ({out.stat().st_size/1e6:.0f} MB)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
