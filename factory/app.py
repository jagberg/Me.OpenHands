"""Factory server: RunView dashboard + API on 127.0.0.1:8766. Runs the shell's single worker thread.

  .venv/bin/python app.py
  POST /api/briefs {title, brief, cfg?}      start a run (cfg defaults to the trial repo + real ignite skills)
  POST /api/runs/<id>/answer {qid, answer}   answer the agent's question; the same conversation resumes
  POST /api/runs/<id>/retry                  re-queue a failed run in the same conversation
  GET  /api/runs                             run records for the dashboard
"""
import json, subprocess, sys, threading, time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

import shell, telegram

ROOT = Path(__file__).resolve().parent.parent
TARGET = Path.home() / ".config" / "factory" / "target.json"  # your repo; see docs/work-repo-setup.md


def ignite_skills():
    """The installed ignite plugin's brief/plan/build skills, newest version (Claude Code's plugin cache)."""
    vers = sorted(Path.home().glob(".claude/plugins/cache/compareclub-ignite/ignite/*/skills"),
                  key=lambda p: [int(x) for x in p.parent.name.split(".") if x.isdigit()])
    return [str(vers[-1] / s) for s in ("brief", "plan", "build")] if vers else []


QA_CFG = {  # verified 2026-10-23 (PR #5): stand-in ignite skills, QA-only checklist, buggy calc.py
    "repo": "jagberg/ai-agent-trial-sandbox",
    "seed_dir": str(ROOT / "bakeoff" / "fixture-qa"),
    "seed_replace": {"/private/tmp/claude-501/bake/pyenv/bin/python -m pytest -q": "python3 -m pytest -q (pip install pytest if missing)"},
    "test_cmd": f"{sys.executable} -m pytest -q",  # host-side check; pytest is in requirements.txt
    "protected": ["test_calc.py"],
}
TRIAL_CFG = {  # real ignite skills (CompareClub plugin, copied per run, never pushed) + OpenSpec + median() feature
    **QA_CFG,
    "seed_dir": str(ROOT / "bakeoff" / "fixture-ignite"), "seed_replace": {},
    "private_skills": ignite_skills(),
}
# target.json (a work repo: repo, test_cmd, protected, overlay_dir) replaces the trial; no seed_dir, so PRs go to the
# repo's default branch and the process files stay out of them.
DEFAULT_CFG = {"private_skills": ignite_skills(), **json.loads(TARGET.read_text())} if TARGET.exists() else TRIAL_CFG
if not DEFAULT_CFG.get("private_skills"):
    print("warning: ignite plugin not found under ~/.claude/plugins/cache; install it in Claude Code", file=sys.stderr)
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
            elif parts[:2] == ["api", "runs"] and parts[-1] == "retry":
                shell.retry(parts[2]); out = {"ok": True}
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
    print("telegram relay:", "on" if telegram.start() else f"off (no {telegram.ENV})", flush=True)
    print(f"factory on http://127.0.0.1:{port}  runs in {shell.RUNS}", flush=True)
    ThreadingHTTPServer(("127.0.0.1", port), H).serve_forever()
