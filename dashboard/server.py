#!/usr/bin/env python3
"""Tiny dashboard server: serves index.html and /api/runs (runs/*/run.json). Usage: python3 dashboard/server.py [port]"""
import json, sys
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

HERE = Path(__file__).resolve().parent
RUNS = HERE.parent / "runs"


class H(BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path.startswith("/api/runs"):
            runs = []
            for p in sorted(RUNS.glob("*/run.json"), reverse=True):
                try:
                    runs.append(json.loads(p.read_text()))
                except ValueError:
                    pass  # mid-write; next poll will get it
            body, ctype = json.dumps(runs).encode(), "application/json"
        elif self.path in ("/", "/index.html"):
            body, ctype = (HERE / "index.html").read_bytes(), "text/html; charset=utf-8"
        else:
            self.send_error(404)
            return
        self.send_response(200)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, *a):
        pass


if __name__ == "__main__":
    port = int(sys.argv[1]) if len(sys.argv) > 1 else 8765
    print(f"dashboard on http://localhost:{port}")
    ThreadingHTTPServer(("127.0.0.1", port), H).serve_forever()
