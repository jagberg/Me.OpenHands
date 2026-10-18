#!/usr/bin/env python3
"""Tiny dashboard server: serves index.html and /api/runs (runs/*/run.json). Usage: python3 dashboard/server.py [port]"""
import json, subprocess, sys, time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

HERE = Path(__file__).resolve().parent
RUNS = HERE.parent / "runs"
_pr = {}  # url -> (ts, state); gh lookups cached 60s


def pr_state(url):
    ts, st = _pr.get(url, (0, None))
    if time.time() - ts > 60:
        try:
            r = subprocess.run(["gh", "pr", "view", url, "--json", "state", "-q", ".state"], capture_output=True, text=True, timeout=10)
            st = r.stdout.strip() or st
        except Exception:
            pass  # gh missing/offline: keep last known
        _pr[url] = (time.time(), st)
    return st


class H(BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path.startswith("/api/runs"):
            runs = []
            for p in sorted(RUNS.glob("*/run.json"), reverse=True):
                try:
                    r = json.loads(p.read_text())
                    r["pr_state"] = pr_state(r["pr_url"]) if r.get("pr_url") else None
                    runs.append(r)
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

    def do_POST(self):
        """Human-in-the-loop actions go to Temporal: answer -> signal, new brief -> start workflow.
        Needs the blueprint venv: blueprint/.venv/bin/python dashboard/server.py"""
        # ponytail: no auth; the server binds to 127.0.0.1 only. Add a token before exposing it on a network.
        import asyncio
        sys.path.insert(0, str(HERE.parent / "blueprint"))
        import worker
        try:
            data = json.loads(self.rfile.read(int(self.headers.get("Content-Length", 0))) or b"{}")
            parts = self.path.strip("/").split("/")  # api/runs/<id>/answer | api/briefs
            if parts[:2] == ["api", "runs"] and parts[-1] == "answer":
                asyncio.run(worker.answer(parts[2], data["qid"], data["answer"]))
                out = {"ok": True}
            elif parts == ["api", "briefs"]:
                out = {"id": asyncio.run(worker.start(data["title"], data["brief"], source=data.get("source", "dashboard")))}
            else:
                return self.send_error(404)
            body, code = json.dumps(out).encode(), 200
        except Exception as e:
            body, code = json.dumps({"error": str(e)}).encode(), 400
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, *a):
        pass


if __name__ == "__main__":
    port = int(sys.argv[1]) if len(sys.argv) > 1 else 8765
    print(f"dashboard on http://localhost:{port}")
    ThreadingHTTPServer(("127.0.0.1", port), H).serve_forever()
