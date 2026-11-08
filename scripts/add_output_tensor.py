#!/usr/bin/env python3
"""Add the missing `output.weight` tensor to a GGUF whose LM head is tied.

llama.cpp's Qwen2Moe loader requires `output.weight`; the converter omits it when the HF model has
tie_word_embeddings=True (ours does — Qwen2.5-0.5B ties the head to the embedding). The dense Qwen2 loader
tolerates the omission, which is why the 0.5B GGUF loads but the MoE one fails with
    check_tensor_dims: tensor 'output.weight' not found

This copies token_embd into output.weight — mathematically identical for a tied model — and writes a new GGUF.

    python scripts/add_output_tensor.py --src in.gguf --out out.gguf
"""
from __future__ import annotations

import argparse
import pathlib
import sys


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--src", required=True)
    ap.add_argument("--out", required=True)
    args = ap.parse_args()

    from gguf import GGUFReader, GGUFValueType, GGUFWriter

    src = pathlib.Path(args.src)
    out = pathlib.Path(args.out)
    r = GGUFReader(str(src))
    if any(t.name == "output.weight" for t in r.tensors):
        print("output.weight already present — nothing to do")
        sys.exit(0)

    _arch = r.fields["general.architecture"].contents()
    arch = _arch[0] if isinstance(_arch, (list, tuple)) else _arch
    if isinstance(arch, bytes):
        arch = arch.decode("utf-8")
    print(f"arch={arch} | tensors={len(r.tensors)} | fields={len(r.fields)}")
    w = GGUFWriter(str(out), arch=arch)

    copied_fields = 0
    for name, field in r.fields.items():
        if name == "general.architecture":
            continue                       # the writer emits this itself
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
            copied_fields += 1
        except Exception as exc:  # noqa: BLE001
            print(f"  !! field {name}: {type(exc).__name__}: {exc}")
    print(f"copied fields: {copied_fields}")

    emb = next((t for t in r.tensors if t.name == "token_embd.weight"), None)
    if emb is None:
        raise SystemExit("no token_embd.weight — cannot tie")
    # quantized tensors: the writer wants the BYTE shape (rows, bytes-per-row); it converts back to logical
    for t in r.tensors:
        w.add_tensor(t.name, t.data, raw_shape=t.data.shape, raw_dtype=t.tensor_type)
    w.add_tensor("output.weight", emb.data, raw_shape=emb.data.shape, raw_dtype=emb.tensor_type)
    print(f"tensors written: {len(r.tensors)} + output.weight (type {emb.tensor_type})")

    w.write_header_to_file()
    w.write_kv_data_to_file()
    w.write_tensors_to_file()
    w.close()
    print(f"wrote {out} ({out.stat().st_size/1e6:.0f} MB)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
