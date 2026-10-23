"""Factory server: RunView dashboard + API on 127.0.0.1:8766. Runs the shell's single worker thread.

  .venv/bin/python app.py
  POST /api/briefs {title, brief, cfg?}      start a run (cfg defaults to the trial repo + loop-back fixture)
  POST /api/runs/<id>/answer {qid, answer}   answer the agent's question; the same conversation resumes
  GET  /api/runs                             run records for the dashboard
"""
import json, subprocess, sys, threading, time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

import shell

ROOT = Path(__file__).resolve().parent.parent
DEFAULT_CFG = {
    "repo": "jagberg/ai-agent-trial-sandbox",
    "seed_dir": str(ROOT / "bakeoff" / "fixture-qa"),          # AGENTS.md, skills, spec, QA-only checklist, buggy calc.py
    "seed_replace": {"/private/tmp/claude-501/bake/pyenv/bin/python -m pytest -q": "python3 -m pytest -q (pip install pytest if missing)"},
    "test_cmd": "/private/tmp/claude-501/bake/pyenv/bin/python -m pytest -q",  # host-side check
    "protected": ["test_calc.py"],
}
_pr: dict = {}

def pr_state(url):
    ts, st = _pr.get(url, (0, None))
    if time.time() - ts > 60:
        r = subprocess.run(["gh", "pr", "view", url, "--json", "state", "-q", ".state"], capture_output=True, text=True)
        _pr[url] = (time.time(), r.stdout.strip() or st)
    return _pr[url][1]


class H(BaseHTTPRequestHandler):
    def send(self, code, body, ctype="application/json"):
        self.send_response(code); self.send_header("Content-Type", ctype); self.send_header("Content-Length", str(len(body)))
        self.end_headers(); self.wfile.write(body)

    def do_GET(self):
        if self.path.startswith("/api/runs"):
            out = []
            for r in shell.runs():
                if r.get("pr_url") and r["status"] == "human_review":
                    st = pr_state(r["pr_url"])
                    if st in ("MERGED", "CLOSED"):  # final human gate: merge/close ends the run
                        r = shell.update(r["id"], lambda x: x.update(status=st.lower(), pr_state=st, finished=shell.now()))
                out.append(r)
            return self.send(200, json.dumps(out).encode())
        if self.path in ("/", "/index.html"):
            return self.send(200, (ROOT / "dashboard" / "index.html").read_bytes(), "text/html; charset=utf-8")
        self.send_error(404)

    def do_POST(self):
        # ponytail: no auth; binds 127.0.0.1 only. Add auth before exposing it on a network.
        try:
            data = json.loads(self.rfile.read(int(self.headers.get("Content-Length", 0))) or b"{}")
            parts = self.path.strip("/").split("/")
            if parts == ["api", "briefs"]:
                out = {"id": shell.start(data["title"], data["brief"], data.get("cfg") or DEFAULT_CFG, data.get("source", "dashboard"))}
            elif parts[:2] == ["api", "runs"] and parts[-1] == "answer":
                shell.answer(parts[2], data["qid"], data["answer"]); out = {"ok": True}
            else:
                return self.send_error(404)
            self.send(200, json.dumps(out).encode())
        except Exception as e:
            self.send(400, json.dumps({"error": str(e)}).encode())

    def log_message(self, *a):
        pass


if __name__ == "__main__":
    port = int(sys.argv[1]) if len(sys.argv) > 1 else 8766
    shell.RUNS.mkdir(parents=True, exist_ok=True)
    threading.Thread(target=shell.worker, daemon=True).start()
    print(f"factory on http://127.0.0.1:{port}  runs in {shell.RUNS}", flush=True)
    ThreadingHTTPServer(("127.0.0.1", port), H).serve_forever()
