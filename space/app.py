#!/usr/bin/env python3
"""SHENNONG HF Space — the judge-facing live demo.

Serves the demo page (docs/demo) plus the query endpoints. **Direct generation, no retrieval, no injected
passages.** The fine-tuned 1.5 B answers from its own weights, side-by-side with the unfine-tuned baseline,
same prompt, same decode, prompts shown. Stdlib only + llama-cpp-python — no torch, no GPU.

    python space/app.py          # serves on 0.0.0.0:7860

Endpoints:
    GET  /                      -> docs/demo/index.html
    GET  /{file}                -> static files from docs/demo
    POST /api/model             -> which model is loaded
    POST /api/query             -> direct generation (fine-tuned 1.5 B)
    POST /api/compare           -> side-by-side vs unfine-tuned baseline
    POST /api/hypothesize       -> hypothesis proposal (fine-tuned 1.5 B)
"""
from __future__ import annotations

import json
import os
import pathlib
import sys
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

DEMO_DIR = ROOT / "docs" / "demo"
PORT = int(os.environ.get("PORT", "7860"))

from shennong.answer import answer_direct, compare_direct, hypothesise_live  # noqa: E402

MIME = {".html": "text/html; charset=utf-8", ".js": "application/javascript",
        ".json": "application/json; charset=utf-8", ".css": "text/css",
        ".png": "image/png", ".svg": "image/svg+xml", ".gguf": "application/octet-stream"}


class Handler(BaseHTTPRequestHandler):
    def _send(self, code, body: bytes, ctype="application/json; charset=utf-8"):
        self.send_response(code)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(body)

    def _json(self, obj, code=200):
        self._send(code, json.dumps(obj, ensure_ascii=False).encode(), "application/json; charset=utf-8")

    def do_GET(self):
        path = self.path.split("?")[0]
        if path in ("/", "/index.html"):
            return self._file("index.html")
        return self._file(path.lstrip("/"))

    def _file(self, rel: str):
        safe = os.path.normpath(rel).lstrip("/")
        full = DEMO_DIR / safe
        if not full.is_file() or not str(full).startswith(str(DEMO_DIR)):
            return self._json({"error": "not found"}, 404)
        return self._send(200, full.read_bytes(), MIME.get(full.suffix, "application/octet-stream"))

    def do_POST(self):
        n = int(self.headers.get("Content-Length") or 0)
        raw = self.rfile.read(min(n, 16_384)) if n else b"{}"
        try:
            payload = json.loads(raw.decode("utf-8") or "{}")
        except json.JSONDecodeError:
            return self._json({"error": "body must be JSON"}, 400)
        q = str(payload.get("question") or payload.get("q") or "")
        mt = int(payload.get("max_new_tokens") or 56)
        if self.path == "/api/model":
            return self._json({"loaded": True, "family": "qwen2.5-1.5b-sft", "params": 1543714304,
                               "note": "fine-tuned 1.5 B GGUF, direct generation + side-by-side baseline"})
        if self.path == "/api/query":
            try:
                return self._json(answer_direct(q, max_new_tokens=mt))
            except Exception as exc:  # noqa: BLE001
                return self._json({"ok": False, "error": f"{type(exc).__name__}: {exc}"}, 500)
        if self.path == "/api/compare":
            try:
                return self._json(compare_direct(q, max_new_tokens=mt))
            except Exception as exc:  # noqa: BLE001
                return self._json({"ok": False, "error": f"{type(exc).__name__}: {exc}"}, 500)
        if self.path == "/api/hypothesize":
            return self._json(hypothesise_live(q, max_new_tokens=mt))
        if self.path == "/api/advise":
            try:
                from shennong.advise import advise
                return self._json(advise(q))
            except Exception as exc:  # noqa: BLE001
                return self._json({"ok": False, "error": f"{type(exc).__name__}: {exc}"}, 500)
        if self.path == "/api/experts":
            try:
                from shennong.experts.router import route_query
                return self._json(route_query(q))
            except Exception as exc:  # noqa: BLE001
                return self._json({"ok": False, "error": f"{type(exc).__name__}: {exc}"}, 500)
        if self.path == "/api/screen":
            try:
                from shennong.screen import fused_screen
                return self._json(fused_screen(q or "COX2", top_k=8))
            except Exception as exc:  # noqa: BLE001
                return self._json({"ok": False, "error": f"{type(exc).__name__}: {exc}"}, 500)
        return self._json({"error": f"no route {self.path}"}, 404)

    def log_message(self, *args):
        pass  # keep the Space log clean


if __name__ == "__main__":
    print(f"SHENNONG Space serving {DEMO_DIR} on 0.0.0.0:{PORT}", flush=True)
    ThreadingHTTPServer(("0.0.0.0", PORT), Handler).serve_forever()
