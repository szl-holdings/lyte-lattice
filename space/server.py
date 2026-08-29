# Copyright 2026 SZL Holdings — SPDX-License-Identifier: Apache-2.0
"""LYTE lattice Hub hologram. Stdlib HTTP on 7860. Not the flagship."""

from __future__ import annotations

import json
import os
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

PORT = int(os.environ.get("PORT", "7860"))
ROOT = Path(__file__).resolve().parent
INDEX = ROOT / "index.html"

ESTATE = {
    "bind": "BIND_AS_A11OY_PACKAGE",
    "product": "https://a-11-oy.com",
    "proof": "https://a11oy.net",
    "source": "https://github.com/szl-holdings/lyte-lattice",
    "product_certified": False,
    "lambda": "Conjecture 1",
    "energy": "UNAVAILABLE",
    "hub_running": "RUNNING only after Hub readback",
    "lyte": "STRUCTURAL-ONLY",
    "never": ["a11oy.com"],
}

CELLS = [
    {"n": "lyte", "title": "Lyte", "honesty": "STRUCTURAL-ONLY"},
    {"n": "N1", "title": "Serve", "honesty": "LIVE"},
    {"n": "N2", "title": "Graph", "honesty": "LIVE"},
    {"n": "N3", "title": "Guard", "honesty": "LIVE"},
    {"n": "N4", "title": "Mosaic", "honesty": "LIVE"},
    {"n": "N5", "title": "Lattice", "honesty": "LIVE"},
    {"n": "N6", "title": "Cover", "honesty": "LIVE"},
    {"n": "N7", "title": "Quant", "honesty": "LIVE"},
    {"n": "N8", "title": "Title", "honesty": "LIVE"},
    {"n": "N9", "title": "Retrieve", "honesty": "LIVE"},
    {"n": "N10", "title": "Observe", "honesty": "LIVE"},
    {"n": "N11", "title": "Tune", "honesty": "LIVE"},
    {"n": "N12", "title": "Schema", "honesty": "LIVE"},
    {"n": "N13", "title": "Energy", "honesty": "LIVE"},
    {"n": "N14", "title": "Tool", "honesty": "LIVE"},
    {"n": "N15", "title": "Memory", "honesty": "LIVE"},
    {"n": "N16", "title": "Eval", "honesty": "LIVE"},
    {"n": "N17", "title": "Mesh", "honesty": "LIVE"},
    {"n": "N18", "title": "Route", "honesty": "LIVE"},
    {"n": "N19", "title": "Cache", "honesty": "LIVE"},
    {"n": "N20", "title": "Voice", "honesty": "LIVE"},
    {"n": "N21", "title": "Sandbox", "honesty": "LIVE"},
    {"n": "N22", "title": "Identity", "honesty": "LIVE"},
    {"n": "N23", "title": "Rails", "honesty": "LIVE"},
    {"n": "N24", "title": "Browser", "honesty": "LIVE"},
    {"n": "N25", "title": "Policy", "honesty": "LIVE"},
    {"n": "N26", "title": "Inference", "honesty": "REPORTED"},
    {"n": "N27", "title": "Train", "honesty": "UNAVAILABLE"},
]


class Handler(BaseHTTPRequestHandler):
    def log_message(self, fmt: str, *args) -> None:
        print(f"{self.command} {self.path} {fmt % args}")

    def _send(self, code: int, body: bytes, ctype: str) -> None:
        self.send_response(code)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        if self.command != "HEAD":
            self.wfile.write(body)

    def do_HEAD(self) -> None:
        self.do_GET()

    def do_GET(self) -> None:
        if self.path in ("/", "/index.html"):
            html = INDEX.read_bytes() if INDEX.is_file() else b"LYTE lattice BIND hologram\n"
            self._send(200, html, "text/html; charset=utf-8")
            return
        if self.path == "/healthz":
            payload = {
                "ok": True,
                "bind": ESTATE["bind"],
                "energy": "UNAVAILABLE",
                "proven_trust": False,
                "product_certified": False,
            }
            self._send(200, json.dumps(payload).encode(), "application/json")
            return
        if self.path == "/api/estate":
            self._send(200, json.dumps(ESTATE).encode(), "application/json")
            return
        if self.path == "/api/cells":
            self._send(200, json.dumps(CELLS).encode(), "application/json")
            return
        self._send(404, b'{"error":"not found"}\n', "application/json")


def main() -> None:
    httpd = ThreadingHTTPServer(("0.0.0.0", PORT), Handler)
    print(f"lyte-lattice hologram on 0.0.0.0:{PORT}")
    httpd.serve_forever()


if __name__ == "__main__":
    main()
