"""Thin shell around the OpenHands agent (ADR 0005).

The process (brief -> plan -> build -> QA, loop-backs, when to ask) lives in the target repo's AGENTS.md and
.agents/skills. This file only does what the agent cannot do reliably:
  - run the agent's commands in a Docker container (OpenHands DockerWorkspace), never on the host;
  - park the run when the agent asks a human, and resume the same conversation with the answer;
  - hard checks before any PR (tests, protected files, QA verdict), sending failures back to the agent;
  - git/gh on the host (your credentials stay out of the container), and the run record the dashboard reads.

Layout per run: runs/<id>/ is mounted at /workspace; the repo is cloned into runs/<id>/repo (/workspace/repo); the
agent server keeps its conversation state in runs/<id>/conversations, outside the repo.
"""
import fnmatch, json, os, queue, shutil, subprocess, threading, time, uuid
from datetime import datetime
from pathlib import Path

os.environ.setdefault("OPENHANDS_SUPPRESS_BANNER", "1")

HERE = Path(__file__).resolve().parent
RUNS = Path(os.environ.get("FACTORY_RUNS", HERE.parent / "runs" / "factory"))
MODEL = os.environ.get("LLM_MODEL", "ollama_chat/qwen3.8-27b-32k")
LLM_BASE_URL = os.environ.get("LLM_BASE_URL", "http://host.docker.internal:11434")  # as seen from the container
SERVER_IMAGE = os.environ.get("AGENT_SERVER_IMAGE", "ghcr.io/openhands/agent-server:1.36.0-python")
GATE = Path(os.environ.get("MODEL_GATE_FILE", Path.home() / "llm-compare" / "STATUS.txt"))  # shared-Mac benchmark gate
MAX_CHECK_RETRIES = 2
now = lambda: datetime.now().isoformat(timespec="seconds")


def sh(cmd, cwd=None, check=True, timeout=600):
    r = subprocess.run(cmd, cwd=cwd, shell=isinstance(cmd, str), capture_output=True, text=True, timeout=timeout)
    if check and r.returncode:
        raise RuntimeError(f"{cmd!r} failed ({r.returncode}):\n{r.stdout}\n{r.stderr}")
    return r


def find_question(final):
    """Exact `QUESTION:` line, else a reply that says it is pausing for the question protocol (bakeoff round 3)."""
    for line in final.splitlines():
        if "QUESTION:" in line:
            return line.split("QUESTION:", 1)[1].strip()
    low = final.lower()
    if "question" in low and ("paus" in low or "answer and i" in low or "waiting for" in low):
        return final.strip()[-300:]
    return None


# ---------- run record (runs/<id>/run.json, read by the dashboard) ----------
LOCK = threading.RLock()

def path(rid): return RUNS / rid / "run.json"
def load(rid): return json.loads(path(rid).read_text())
def runs(): return [json.loads(p.read_text()) for p in sorted(RUNS.glob("*/run.json"), reverse=True)]

def update(rid, fn):
    with LOCK:
        r = load(rid); fn(r)
        tmp = path(rid).with_suffix(".tmp"); tmp.write_text(json.dumps(r, indent=2)); tmp.replace(path(rid))
        return r

def event(rid, kind, msg=""):
    update(rid, lambda r: r["events"].append({"ts": now(), "kind": kind, "msg": msg}))


# ---------- public API: start a run, answer a question ----------
JOBS: "queue.Queue[tuple[str, str]]" = queue.Queue()  # (run id, message); one agent at a time (one local model)

def start(title, brief, cfg, source="dashboard"):
    rid = "run-" + datetime.now().strftime("%Y%m%d-%H%M%S")
    d = RUNS / rid; d.mkdir(parents=True)
    r = {"id": rid, "title": title, "problem": brief, "source": source, "engine": "openhands", "model": MODEL,
         "repo": cfg["repo"], "cfg": cfg, "status": "queued", "created": now(), "started": now(), "current_stage": None,
         "conversation_id": None, "questions": [], "stages": [], "events": [], "checks": {}, "check_attempts": 0,
         "pr_url": None, "pr_state": None, "summary": "", "resolution": "", "error": None}
    path(rid).write_text(json.dumps(r, indent=2))
    try:
        setup_repo(rid)
    except Exception as e:
        update(rid, lambda r: r.update(status="failed", error=str(e)[-1500:]))
        raise
    JOBS.put((rid, f"Ticket: {title}\n{brief}\nFollow the process in AGENTS.md."))
    event(rid, "queued", f"ticket from {source}")
    return rid

def answer(rid, qid, text):
    def f(r):
        q = next(q for q in r["questions"] if q["id"] == qid and q["status"] == "open")
        q.update(status="answered", answer=text, answered_at=now()); r["status"] = "queued"
    update(rid, f)
    event(rid, "answered", f"{qid}: {text[:120]}")
    JOBS.put((rid, f"Answer from the product owner: {text}"))


# ---------- host side: repo, checks, PR ----------
def setup_repo(rid):
    r = load(rid); c = r["cfg"]; repo = RUNS / rid / "repo"
    sh(["git", "clone", "-q", "--depth", "1", f"git@github.com:{c['repo']}.git", str(repo)])
    sh(["git", "config", "user.name", "OpenHands factory"], cwd=repo)
    sh(["git", "config", "user.email", "openhands@localhost"], cwd=repo)
    base = sh(["git", "rev-parse", "--abbrev-ref", "HEAD"], cwd=repo).stdout.strip()
    if c.get("seed_dir"):  # throwaway base branch holding a seeded snapshot (process files + code); default branch untouched
        base = f"ai-eval/base-{rid}"
        sh(["git", "checkout", "-q", "-b", base], cwd=repo)
        shutil.copytree(c["seed_dir"], repo, dirs_exist_ok=True, ignore=shutil.ignore_patterns(".git"))
        for old, new in c.get("seed_replace", {}).items():  # e.g. point AGENTS.md at the container's test command
            p = repo / "AGENTS.md"; p.write_text(p.read_text().replace(old, new))
        sh(["git", "add", "-A"], cwd=repo); sh(["git", "commit", "-q", "-m", "chore: seed factory test snapshot"], cwd=repo)
    sh(["git", "checkout", "-q", "-b", f"ai/{rid}"], cwd=repo)
    update(rid, lambda r: r.update(base_branch=base, head_branch=f"ai/{rid}"))

def run_checks(rid):
    r = load(rid); c = r["cfg"]; repo = RUNS / rid / "repo"
    t = sh(c["test_cmd"], cwd=repo, check=False)
    changed = sh(["git", "status", "--porcelain"], cwd=repo).stdout.splitlines()
    touched = [l[3:] for l in changed if any(fnmatch.fnmatch(Path(l[3:]).name, g) for g in c.get("protected", []))]
    qa = repo / ".ignite" / "qa.md"
    verdict = next((l for l in (qa.read_text().splitlines() if qa.exists() else [])[::-1] if "VERDICT" in l.upper()), "")
    checks = {"tests_pass": t.returncode == 0, "protected_files_untouched": not touched,
              "qa_verdict_pass": "PASS" in verdict.upper(), "has_changes": bool(changed)}
    feedback = []
    if not checks["tests_pass"]: feedback.append(f"The test command `{c['test_cmd']}` fails:\n{(t.stdout + t.stderr)[-1200:]}")
    if touched: feedback.append(f"You edited protected files {touched}; revert them.")
    if not checks["qa_verdict_pass"]: feedback.append("qa-review has not recorded `VERDICT: PASS` in .ignite/qa.md; finish the process.")
    if not checks["has_changes"]: feedback.append("No changes were made.")
    return checks, "\n".join(feedback)

def open_pr(rid):
    r = load(rid); repo = RUNS / rid / "repo"; log = repo / ".ignite" / "log.md"
    sh(["git", "add", "-A"], cwd=repo)
    sh(["git", "commit", "-q", "-m", f"fix: {r['title']}\n\nAuthored by the OpenHands agent (factory run {rid})."], cwd=repo)
    if r["base_branch"].startswith("ai-eval/"):
        sh(["git", "push", "-q", "origin", r["base_branch"]], cwd=repo)
    sh(["git", "push", "-q", "origin", r["head_branch"]], cwd=repo)
    decided = "".join(f"- {q['text']} -> **{q['answer']}**\n" for q in r["questions"] if q["status"] == "answered")
    body = (f"## Summary\n{r['summary']}\n\n## Human decisions\n{decided or 'none'}\n\n## Process log (from the agent)\n"
            f"```\n{log.read_text() if log.exists() else 'none'}\n```\n\n## Checks\n"
            + "".join(f"- {'✅' if v else '❌'} {k.replace('_', ' ')}\n" for k, v in r["checks"].items())
            + f"\nModel `{r['model']}`, run `{rid}`. A human reviews and merges.\n")
    out = sh(["gh", "pr", "create", "--repo", r["repo"], "--base", r["base_branch"], "--head", r["head_branch"],
              "--title", f"{r['title']} [{rid}]", "--body", body], cwd=repo).stdout.strip()
    return out.splitlines()[-1]


# ---------- agent side: one turn of the conversation, in Docker ----------
def agent_turn(rid, message):
    from openhands.sdk import LLM, Agent, AgentContext, Conversation
    from openhands.sdk.conversation.response_utils import get_agent_final_response
    from openhands.sdk.skills import load_project_skills
    from openhands.tools.preset.default import get_default_tools
    from openhands.workspace import DockerWorkspace

    r = load(rid); d = RUNS / rid
    llm = LLM(model=MODEL, base_url=LLM_BASE_URL, api_key=os.environ.get("LLM_API_KEY", "ollama"),  # dummy for Ollama
              max_input_tokens=32768, max_output_tokens=8192, timeout=900, native_tool_calling=True, usage_id="agent")
    # reasoning left on: with skills loaded and reasoning off, qwen3 returned empty replies (bakeoff round 1)
    skills = load_project_skills(d / "repo")  # repo's .agents/skills + AGENTS.md, read on the host
    agent = Agent(llm=llm, tools=get_default_tools(enable_browser=False)[:2],
                  agent_context=AgentContext(skills=skills, load_user_skills=False, load_public_skills=False,
                                             system_message_suffix="The repository is at /workspace/repo. Work there."))
    # The agent server leases a conversation for 45 s and a stopped container does not release it, so a resume that
    # arrives sooner gets ConversationLeaseHeldError (seen 2026-10-23). Wait out the rest of the lease.
    # ponytail: fixed wait; only matters when an answer comes back within seconds (scripted tests, not humans).
    last = r.get("turns", [{}])[-1].get("ended") if r.get("turns") else None
    if last and r["conversation_id"]:
        time.sleep(max(0.0, 50 - (time.time() - last)))
    t0 = time.time()
    with DockerWorkspace(server_image=SERVER_IMAGE, platform="linux/arm64", volumes=[f"{d}:/workspace"]) as w:
        cid = uuid.UUID(r["conversation_id"]) if r["conversation_id"] else None
        conv = Conversation(agent=agent, workspace=w, conversation_id=cid, visualizer=None, max_iteration_per_run=120)
        update(rid, lambda r: r.update(conversation_id=str(conv.id)))
        conv.send_message(message)
        conv.run()
        final = get_agent_final_response(conv.state.events) or ""
        try:
            m = conv.conversation_stats.get_combined_metrics(); u = m.accumulated_token_usage
            stats = {"llm_calls": len(m.response_latencies), "prompt_tokens": u.prompt_tokens, "completion_tokens": u.completion_tokens}
        except Exception:
            stats = {}
        conv.close()  # keeps the conversation (delete_on_close=False) but lets the server release what it can
    return final, round(time.time() - t0, 1), stats


def stages_from_log(rid):
    log = RUNS / rid / "repo" / ".ignite" / "log.md"
    lines = [l for l in (log.read_text().splitlines() if log.exists() else []) if ":" in l]
    return [{"name": l.split(":", 1)[0].strip(), "status": "done", "note": l.split(":", 1)[1].strip()} for l in lines]


def step(rid, message):
    """One agent turn, then: park on a question, or check -> (feedback | PR)."""
    update(rid, lambda r: r.update(status="running", current_stage="agent"))
    event(rid, "agent_turn", message[:120])
    final, secs, stats = agent_turn(rid, message)
    def rec(r):
        r["stages"] = stages_from_log(rid)
        r.setdefault("turns", []).append({"ts": now(), "ended": time.time(), "seconds": secs, **stats, "final": final[-600:]})
        if r["stages"]:  # dashboard sums these; put the run's totals on the last stage row
            tot = lambda k: sum(t.get(k, 0) for t in r["turns"])
            r["stages"][-1].update(duration_s=tot("seconds"), llm_calls=tot("llm_calls"),
                                   prompt_tokens=tot("prompt_tokens"), completion_tokens=tot("completion_tokens"))
    update(rid, rec)
    q = find_question(final)
    if q:
        def ask(r):
            r["questions"].append({"id": f"q{len(r['questions']) + 1}", "text": q, "blocking": True, "status": "open",
                                   "stage": (r["stages"][-1]["name"] if r["stages"] else "agent"), "asked_at": now()})
            r.update(status="awaiting_decision", current_stage="waiting for a human")
        update(rid, ask)
        event(rid, "question", q[:200])
        return
    checks, feedback = run_checks(rid)
    r = update(rid, lambda r: r.update(checks=checks, summary=final[-1500:]))
    if feedback and r["check_attempts"] < MAX_CHECK_RETRIES:
        update(rid, lambda r: r.update(check_attempts=r["check_attempts"] + 1))
        event(rid, "checks_failed", feedback[:200])
        return JOBS.put((rid, "The factory's checks failed. Fix this and finish the process again:\n" + feedback))
    if feedback:
        update(rid, lambda r: r.update(status="failed", error="checks failed: " + feedback[:1500]))
        return event(rid, "failed", "checks failed after retries")
    url = open_pr(rid)
    update(rid, lambda r: r.update(pr_url=url, pr_state="OPEN", pr_opened=now(), status="human_review", current_stage="human review"))
    event(rid, "pr_opened", url)


def gate_open():
    return not GATE.exists() or GATE.read_text().splitlines()[:1] == ["STATE: READY"]


def worker():
    while True:
        rid, msg = JOBS.get()
        while not gate_open():  # ponytail: poll a file; fine for one shared Mac
            time.sleep(60)
        try:
            step(rid, msg)
        except Exception as e:
            update(rid, lambda r: r.update(status="failed", error=f"{type(e).__name__}: {e}"[-1500:]))
            event(rid, "failed", str(e)[:200])
