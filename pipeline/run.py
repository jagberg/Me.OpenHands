#!/usr/bin/env python3
"""Local OpenHands eval pipeline: ignite stages -> fix -> verify -> PR -> dashboard metrics.

Run with the OpenHands tool venv (it has the SDK):
  ~/.local/share/uv/tools/openhands/bin/python pipeline/run.py [--no-pr]
Uses local Ollama only. No API keys: LLM_API_KEY is a dummy placeholder for litellm.
"""
import argparse, json, os, shutil, subprocess, sys, time, traceback
from datetime import datetime
from pathlib import Path

os.environ.setdefault("OPENHANDS_SUPPRESS_BANNER", "1")

ROOT = Path(__file__).resolve().parent.parent
SKILLS = ROOT / "pipeline" / "skills"
SANDBOX = Path.home() / "code" / "openhands-sandbox"
TARGET_REPO = "jagberg/Me.Compass"
TARGET_SSH = f"git@github.com:{TARGET_REPO}.git"
EVAL_DIR = "evals/openhands-sandbox"
TEST_CMD = "uv run --with pytest pytest -q"
MODEL = os.environ.get("OH_MODEL", "ollama_chat/qwen3-14b-oh")
OLLAMA = os.environ.get("OH_BASE_URL", "http://localhost:11434")
PROBLEM = ("The test suite in this folder fails: test_calc.py::test_average. "
           "average() in calc.py returns the wrong value. Find the root cause and fix it.")
STAGES = ["ignite-intent", "ignite-brief", "ignite-plan", "implement"]


def sh(cmd, cwd=None, check=True, timeout=300):
    r = subprocess.run(cmd, cwd=cwd, shell=isinstance(cmd, str), capture_output=True, text=True, timeout=timeout)
    if check and r.returncode:
        raise RuntimeError(f"{cmd!r} failed ({r.returncode}):\n{r.stdout}\n{r.stderr}")
    return r


class Run:
    """Run record persisted to runs/<id>/run.json after every change (dashboard reads it live)."""
    def __init__(self, run_id):
        self.dir = ROOT / "runs" / run_id
        self.dir.mkdir(parents=True)
        self.d = {"id": run_id, "started": datetime.now().isoformat(timespec="seconds"), "status": "running",
                  "model": MODEL, "problem": PROBLEM, "repo": TARGET_REPO, "stages": [], "pr_url": None,
                  "tests": {}, "diff": {}, "summary": "", "error": None}
        self.save()

    def save(self):
        (self.dir / "run.json").write_text(json.dumps(self.d, indent=2))


def make_llm():
    from openhands.sdk import LLM
    return LLM(model=MODEL, base_url=OLLAMA, api_key="ollama",  # dummy; Ollama ignores it
               reasoning_effort="none", timeout=900, num_retries=2,
               max_input_tokens=32768, max_output_tokens=4096, native_tool_calling=True,
               litellm_extra_body={"options": {"num_ctx": 32768}}, usage_id="agent")


def run_stage(name, workdir, task):
    """One OpenHands conversation. Returns stage record with metrics from the SDK."""
    from openhands.sdk import Agent, AgentContext, Conversation
    from openhands.sdk.conversation.response_utils import get_agent_final_response
    from openhands.sdk.event import ActionEvent
    from openhands.tools.preset.default import get_default_tools

    agent = Agent(llm=make_llm(), tools=get_default_tools(enable_browser=False)[:2],  # terminal + file_editor
                  agent_context=AgentContext(load_user_skills=False, load_public_skills=False))
    actions = []
    conv = Conversation(agent=agent, workspace=str(workdir), visualizer=None, max_iteration_per_run=40,
                        callbacks=[lambda e: actions.append(e) if isinstance(e, ActionEvent) else None])
    skill = (SKILLS / f"{name}.md").read_text()
    t0 = time.time()
    rec = {"name": name, "status": "running", "started": datetime.now().isoformat(timespec="seconds")}
    try:
        conv.send_message(f"{skill}\n\n## Context\nWorking folder: {EVAL_DIR} (relative to cwd).\n"
                          f"Test command (run inside that folder): `{TEST_CMD}`\n\n## Problem\n{task}")
        conv.run()
        rec["status"] = "done"
        rec["final_message"] = get_agent_final_response(conv.state.events)
    except Exception as e:  # keep metrics even when the stage blows up
        rec["status"] = "error"
        rec["error"] = f"{type(e).__name__}: {e}"
    m = conv.conversation_stats.get_combined_metrics()
    u = m.accumulated_token_usage
    lat = [x.latency for x in m.response_latencies]
    rec.update({"duration_s": round(time.time() - t0, 1), "llm_calls": len(lat),
                "prompt_tokens": getattr(u, "prompt_tokens", 0), "completion_tokens": getattr(u, "completion_tokens", 0),
                "avg_latency_s": round(sum(lat) / len(lat), 1) if lat else 0, "cost_usd": m.accumulated_cost,
                "tool_calls": len(actions), "tools": sorted({a.tool_name for a in actions}),
                "conversation_id": str(conv.id)})
    conv.close()
    return rec


def run_tests(workdir):
    r = sh(TEST_CMD, cwd=workdir / EVAL_DIR, check=False)
    return {"passed": r.returncode == 0, "output": (r.stdout + r.stderr)[-1500:]}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--no-pr", action="store_true", help="skip push + PR (local only)")
    args = ap.parse_args()

    run = Run(datetime.now().strftime("%Y%m%d-%H%M%S"))
    d = run.d
    ws = run.dir / "workspace"
    base_br, fix_br = f"openhands-eval/base-{d['id']}", f"openhands/fix-{d['id']}"
    try:
        sh(["git", "clone", "-q", "--depth", "1", TARGET_SSH, str(ws)])
        sh(["git", "checkout", "-q", "-b", base_br], cwd=ws)
        (ws / EVAL_DIR).mkdir(parents=True)
        for f in ("calc.py", "test_calc.py"):
            shutil.copy(SANDBOX / f, ws / EVAL_DIR / f)
        sh(["git", "add", "-A"], cwd=ws)
        sh(["git", "commit", "-q", "-m", "chore(evals): add openhands sandbox with failing test"], cwd=ws)
        base_sha = sh(["git", "rev-parse", "HEAD"], cwd=ws).stdout.strip()
        sh(["git", "checkout", "-q", "-b", fix_br], cwd=ws)
        d["tests"]["before"] = run_tests(ws)
        run.save()
        if d["tests"]["before"]["passed"]:
            raise RuntimeError("sandbox test already passes; nothing to fix")

        for name in STAGES:
            rec = {"name": name, "status": "running"}
            d["stages"].append(rec); run.save()
            rec.update(run_stage(name, ws, PROBLEM))
            run.save()
            if rec["status"] != "done":
                raise RuntimeError(f"stage {name} failed: {rec.get('error')}")

        d["tests"]["after"] = run_tests(ws)
        d["diff"] = {"stat": sh(["git", "diff", "--stat", "--", EVAL_DIR + "/calc.py", EVAL_DIR + "/test_calc.py"], cwd=ws).stdout,
                     "patch": sh(["git", "diff", "--", EVAL_DIR + "/calc.py", EVAL_DIR + "/test_calc.py"], cwd=ws).stdout}
        d["artifacts"] = {n: (ws / EVAL_DIR / ".ignite" / f"{n}.md").read_text()
                          for n in ("intent", "brief", "plan") if (ws / EVAL_DIR / ".ignite" / f"{n}.md").exists()}
        d["summary"] = d["stages"][-1].get("final_message", "")
        test_edited = bool(sh(["git", "diff", "--name-only", "--", EVAL_DIR + "/test_calc.py"], cwd=ws).stdout.strip())
        d["checks"] = {"tests_pass_after": d["tests"]["after"]["passed"], "test_file_untouched": not test_edited}
        run.save()
        if not all(d["checks"].values()):
            raise RuntimeError(f"verification failed: {d['checks']}")

        if not args.no_pr:
            sh(["git", "add", "-A"], cwd=ws)
            sh(["git", "commit", "-q", "-m", "fix(evals): correct average() divisor\n\nAuthored by OpenHands (local Ollama).\n\nCo-Authored-By: OpenHands <openhands@all-hands.dev>"], cwd=ws)
            sh(["git", "push", "-q", "origin", base_br], cwd=ws)  # PR base = buggy snapshot; master untouched
            sh(["git", "push", "-q", "origin", fix_br], cwd=ws)
            tot = lambda k: sum(s.get(k, 0) for s in d["stages"])
            body = (f"## Summary\n{d['summary']}\n\n## Metrics (local OpenHands, `{MODEL}`)\n"
                    f"- Stages: {len(d['stages'])} | LLM calls: {tot('llm_calls')} | tool calls: {tot('tool_calls')}\n"
                    f"- Tokens: {tot('prompt_tokens')} in / {tot('completion_tokens')} out | wall time: {round(tot('duration_s'))}s | cost: $0 (local)\n"
                    f"- Tests: before FAIL, after PASS\n\nBase branch is a throwaway snapshot; master is untouched. Safe to close and delete both branches.\n\n"
                    f"🤖 Generated with OpenHands (local pipeline)")
            r = sh(["gh", "pr", "create", "--repo", TARGET_REPO, "--base", base_br, "--head", fix_br,
                    "--title", f"fix(evals): average() divisor [openhands {d['id']}]", "--body", body], cwd=ws)
            d["pr_url"] = r.stdout.strip().splitlines()[-1]
        d["status"] = "success"
    except Exception as e:
        d["status"] = "failed"
        d["error"] = f"{e}\n{traceback.format_exc()[-1200:]}"
    d["finished"] = datetime.now().isoformat(timespec="seconds")
    run.save()
    print(json.dumps({k: d[k] for k in ("id", "status", "pr_url", "error")}, indent=2))
    return 0 if d["status"] == "success" else 1


if __name__ == "__main__":
    sys.exit(main())
