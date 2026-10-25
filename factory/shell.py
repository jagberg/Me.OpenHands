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
import base64, fnmatch, json, os, queue, shutil, subprocess, threading, time, uuid
from datetime import datetime
from pathlib import Path

os.environ.setdefault("OPENHANDS_SUPPRESS_BANNER", "1")

HERE = Path(__file__).resolve().parent
RUNS = Path(os.environ.get("FACTORY_RUNS", HERE.parent / "runs" / "factory"))
MODEL = os.environ.get("LLM_MODEL", "ollama_chat/qwen3.8-27b-32k")
LLM_BASE_URL = os.environ.get("LLM_BASE_URL", "http://host.docker.internal:11434")  # as seen from the container
SERVER_IMAGE = os.environ.get("AGENT_SERVER_IMAGE", "ghcr.io/openhands/agent-server:1.21.0-python")  # must match openhands-sdk (requirements.txt)
GATE = Path(os.environ.get("MODEL_GATE_FILE", Path.home() / "llm-compare" / "STATUS.txt"))  # shared-Mac benchmark gate
PLATFORM = "linux/arm64" if os.uname().machine == "arm64" else "linux/amd64"  # DockerWorkspace defaults to amd64
MAX_CHECK_RETRIES = 2
LANGFUSE_ENV = Path.home() / ".config" / "factory" / "langfuse.env"
OTEL_KEYS = ["OTEL_EXPORTER_OTLP_TRACES_ENDPOINT", "OTEL_EXPORTER_OTLP_TRACES_HEADERS", "OTEL_EXPORTER_OTLP_TRACES_PROTOCOL"]
now =lambda: datetime.now().isoformat(timespec="seconds")


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
    # run-20261024-151022: "Stopping to ask the product owner (see QUESTION line above)" with the line in an earlier message
    if "question" in low and ("paus" in low or "answer and i" in low or "waiting for" in low or "stopping to ask" in low):
        return final.strip()[-300:]
    return None


MAX_NUDGES = 6  # per turn; then the host checks decide
NUDGE = ("Continue the process: do the next step with a tool now. When you need a human, write the QUESTION line. "
         "When the whole process is finished, call the finish tool.")


def ended_on_text(events):
    """True if the agent's last word was a plain message rather than the finish tool."""
    for e in reversed(events):
        if getattr(e, "source", None) != "agent":
            continue
        if type(e).__name__ == "MessageEvent":
            return True
        if type(e).__name__ == "ActionEvent":
            return getattr(e, "tool_name", None) != "finish"
    return False


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

NOTIFY = []  # callables (rid, kind, msg), e.g. telegram.notify

def event(rid, kind, msg=""):
    update(rid, lambda r: r["events"].append({"ts": now(), "kind": kind, "msg": msg}))
    for f in NOTIFY: f(rid, kind, msg)


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
    if text.strip().lower().startswith("approve"):  # human gate in code (ADR 0002): only a human approves a brief
        for b in (RUNS / rid / "repo").glob("intent/*/brief.md"):
            if "\nStatus: draft" in b.read_text():
                b.write_text(b.read_text().replace("\nStatus: draft", "\nStatus: approved", 1))
                event(rid, "approved", str(b.relative_to(RUNS / rid / "repo")))
    JOBS.put((rid, f"Answer from the product owner: {text}"))


def retry(rid):
    """Re-queue a failed run in its same conversation (e.g. the Mac slept and the container start timed out)."""
    def f(r):
        assert r["status"] == "failed", f"run is {r['status']}, not failed"
        r.update(status="queued", check_attempts=0, error=None)
    update(rid, f)
    event(rid, "retried")
    JOBS.put((rid, "The previous turn was interrupted. Check the repo state and continue the process from where it stopped."))


# ---------- host side: repo, checks, PR ----------
def setup_repo(rid):
    r = load(rid); c = r["cfg"]; repo = RUNS / rid / "repo"
    sh(["gh", "repo", "clone", c["repo"], str(repo), "--", "-q", "--depth", "1"])  # gh's own protocol and host login
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
    exclude = lambda rel: open(repo / ".git" / "info" / "exclude", "a").write(f"/{rel}\n")
    for src in c.get("private_skills", []):  # e.g. the ignite plugin's skills: copied per run, never committed or pushed
        src = Path(src).expanduser(); shutil.copytree(src, repo / ".agents" / "skills" / src.name)
        exclude(f".agents/skills/{src.name}/")
    if c.get("overlay_dir"):  # process files for a repo that doesn't carry them (AGENTS.md, knowledge, skills): same rule
        ov = Path(c["overlay_dir"]).expanduser()
        for f in (f for f in sorted(ov.rglob("*")) if f.is_file()):
            rel = f.relative_to(ov)
            if (repo / rel).exists():
                raise RuntimeError(f"{rel} already exists in {c['repo']}; drop it from the overlay {ov}")
            (repo / rel).parent.mkdir(parents=True, exist_ok=True); shutil.copy2(f, repo / rel); exclude(rel)
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
    unapproved = [str(b.relative_to(repo)) for b in repo.glob("intent/*/brief.md") if "\nStatus: approved" not in b.read_text()]
    if list(repo.glob("intent/*/brief.md")):
        checks["brief_approved"] = not unapproved
    feedback = []
    if unapproved: feedback.append(f"Briefs not approved by a human: {unapproved}. Ask for approval with a QUESTION.")
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
def langfuse_otel(rid):
    """OTLP settings for the agent server's built-in tracing (openhands/sdk/observability/laminar.py), sent through the
    OTel collector in observability/langfuse, which stamps X-Factory-Run on every span as session.id so Langfuse groups
    a run's traces. Optional: ~/.config/factory/langfuse.env (chmod 600) with LANGFUSE_PUBLIC_KEY=, LANGFUSE_SECRET_KEY=
    and OTLP_ENDPOINT= as seen from the container (default: the local collector)."""
    if not LANGFUSE_ENV.exists():
        return {}
    c = dict(l.split("=", 1) for l in LANGFUSE_ENV.read_text().split() if "=" in l)
    auth = base64.b64encode(f"{c['LANGFUSE_PUBLIC_KEY']}:{c['LANGFUSE_SECRET_KEY']}".encode()).decode()
    endpoint = c.get("OTLP_ENDPOINT", "http://host.docker.internal:4318/v1/traces")
    return dict(zip(OTEL_KEYS, [endpoint, f"Authorization=Basic%20{auth},X-Factory-Run={rid}", "http/protobuf"]))

def agent_turn(rid, message):
    from openhands.sdk import LLM, Agent, AgentContext, Conversation
    from openhands.sdk.context.condenser import LLMSummarizingCondenser
    from openhands.sdk.conversation.response_utils import get_agent_final_response
    from openhands.sdk.skills import load_project_skills
    from openhands.tools.preset.default import get_default_tools
    from openhands.workspace import DockerWorkspace

    r = load(rid); d = RUNS / rid
    llm = LLM(model=MODEL, base_url=LLM_BASE_URL, api_key=os.environ.get("LLM_API_KEY", "ollama"),  # dummy for Ollama
              max_input_tokens=32768, max_output_tokens=8192, timeout=900, native_tool_calling=True, usage_id="agent")
    # reasoning left on: with skills loaded and reasoning off, qwen3 returned empty replies (bakeoff round 1)
    skills = load_project_skills(d / "repo")  # repo's .agents/skills + AGENTS.md, read on the host
    # The ignite + OpenSpec skills are ~60 KB; summarise older history so a long turn fits the 32k window.
    condenser = LLMSummarizingCondenser(llm=llm.model_copy(update={"usage_id": "condenser"}), max_tokens=24000, keep_first=2)
    agent = Agent(llm=llm, tools=get_default_tools(enable_browser=False)[:2], condenser=condenser,
                  agent_context=AgentContext(skills=skills, load_user_skills=False, load_public_skills=False,
                                             system_message_suffix="The repository is at /workspace/repo. Work there."))
    # The agent server leases a conversation for 45 s and a stopped container does not release it, so a resume that
    # arrives sooner gets ConversationLeaseHeldError (seen 2026-10-23). Wait out the rest of the lease.
    # ponytail: fixed wait; only matters when an answer comes back within seconds (scripted tests, not humans).
    last = max([t["ended"] for t in r.get("turns", [])[-1:]] + [r.get("failed_at") or 0])  # a failed turn holds it too
    if last and r["conversation_id"]:
        time.sleep(max(0.0, 50 - (time.time() - last)))
    # Only the agent server in Docker (where the LLM calls happen) traces, via forward_env, which reads os.environ when
    # the container starts. The keys are removed again at once: with them set, the host SDK's lazy observe() turns on
    # too and crashes on its older lmnr 0.8.0 ("unexpected keyword argument 'rollout_entrypoint'", 2026-10-25).
    os.environ.update(langfuse_otel(rid))
    t0 = time.time()
    try:
        ws = DockerWorkspace(server_image=SERVER_IMAGE, platform=PLATFORM, volumes=[f"{d}:/workspace"],
                             forward_env=["DEBUG", *OTEL_KEYS])
    finally:
        for k in OTEL_KEYS:
            os.environ.pop(k, None)
    with ws as w:
        cid = uuid.UUID(r["conversation_id"]) if r["conversation_id"] else None
        # delete_on_close=False: the factory default is True, and close() then deletes the conversation server-side, so
        # every resume silently started a fresh one (runs 2026-10-23..24; found because conversations/ was empty).
        conv = Conversation(agent=agent, workspace=w, conversation_id=cid, visualizer=None, max_iteration_per_run=120,
                            delete_on_close=False)
        update(rid, lambda r: r.update(conversation_id=str(conv.id)))
        conv.send_message(message)
        for _ in range(MAX_NUDGES + 1):
            conv.run()
            final = get_agent_final_response(conv.state.events) or ""
            # A plain text reply ends the run in the SDK; qwen does this mid-process ("Let me view the file.").
            # Done = the finish tool or a QUESTION; anything else gets a nudge in the same container.
            if find_question(final) or not ended_on_text(conv.state.events):
                break
            conv.send_message(NUDGE)
        try:
            m = conv.conversation_stats.get_combined_metrics(); u = m.accumulated_token_usage
            stats = {"llm_calls": len(m.response_latencies), "prompt_tokens": u.prompt_tokens, "completion_tokens": u.completion_tokens}
        except Exception:
            stats = {}
        conv.close()  # stops the websocket; the conversation stays in runs/<id>/conversations for the next turn
    return final, round(time.time() - t0, 1), stats


def stages_from_log(rid):
    log = RUNS / rid / "repo" / ".ignite" / "log.md"
    lines = [l for l in (log.read_text().splitlines() if log.exists() else []) if ":" in l]
    stages = [{"name": l.split(":", 1)[0].strip(), "status": "done", "note": l.split(":", 1)[1].strip()} for l in lines]
    return stage_metrics(rid, lines, stages)


def stage_metrics(rid, lines, stages):
    """Per-stage agent time, LLM calls, tokens and tools from the persisted OpenHands events. A stage starts at the
    action that appended its line to .ignite/log.md. Gaps that end in a user message (a human answer or factory
    feedback) are waiting, not agent time."""
    d = RUNS / rid / "conversations"
    evs = sorted((json.loads(p.read_text()) for p in d.glob("*/events/*.json")), key=lambda e: e["timestamp"])
    if not evs:
        return stages
    ts = [datetime.fromisoformat(e["timestamp"]).timestamp() for e in evs]
    starts, i = [], 0
    for line in lines:  # first action at/after the previous stage start that wrote this log line
        key = line[:40]
        i = next((j for j in range(i, len(evs)) if evs[j]["kind"] == "ActionEvent" and key in json.dumps(evs[j])), None)
        if i is None:
            return stages  # log line not found in the events (edited by hand?): keep stages without metrics
        starts.append(i)
    usage = lambda e: [sum(u["accumulated_token_usage"][k] for u in e["value"]["usage_to_metrics"].values())
                       for k in ("prompt_tokens", "completion_tokens")]
    lat = {}
    for st in d.glob("*/base_state.json"):
        for u in json.loads(st.read_text()).get("stats", {}).get("usage_to_metrics", {}).values():
            lat.update({x["response_id"]: x["latency"] for x in u.get("response_latencies", [])})
    cum, cum_at, kinds, tix, turn = [0, 0], [], [], [], 0
    for e in evs:
        if e["kind"] == "ConversationStateUpdateEvent" and e.get("key") == "stats":
            cum = usage(e)
        cum_at.append(cum)
        k = user_kind(e)
        turn += k not in (None, "nudges")  # every message but a nudge starts a new shell turn
        kinds.append(k); tix.append(turn)
    # Which user message each gap (ts[j-1]..ts[j]) leads into. A resumed container writes a state update a few ms
    # before the human's answer, which hid every wait as agent time (run-20261025-200741), so a state update under 1 s
    # before a user message counts as that message.
    ends = [None] * len(evs)
    for j in range(len(evs) - 1, -1, -1):
        if evs[j]["kind"] == "MessageEvent" and evs[j]["source"] == "user":
            ends[j] = kinds[j]
        elif evs[j]["kind"] == "ConversationStateUpdateEvent" and j + 1 < len(evs) and ts[j + 1] - ts[j] < 1:
            ends[j] = ends[j + 1]
    starts[0] = 0  # reading AGENTS.md etc. before the first log line is first-stage work
    for n, (s, a) in enumerate(zip(stages, starts)):
        b = starts[n + 1] if n + 1 < len(starts) else len(evs)  # the LLM call that wrote a stage's log line counts to it
        acts = [e for e in evs[a:b] if e["kind"] == "ActionEvent"]
        calls = {e["llm_response_id"] for e in evs[a:b] if e.get("llm_response_id")}  # actions + final replies
        work = sum(ts[j] - ts[j - 1] for j in range(max(a, 1), b) if not ends[j])
        before = cum_at[a - 1] if a else [0, 0]
        known = [lat[c] for c in calls if c in lat]
        s.update(duration_s=round(work), llm_calls=len(calls), tool_calls=len(acts),
                 prompt_tokens=cum_at[b - 1][0] - before[0], completion_tokens=cum_at[b - 1][1] - before[1],
                 avg_latency_s=round(sum(known) / len(known), 1) if known else None,
                 turn_ids={tix[j] for j in range(a, b) if evs[j]["kind"] == "ActionEvent"},
                 wait_s=round(sum(ts[j] - ts[j - 1] for j in range(max(a, 1), b) if ends[j] == "prompts")),
                 lead_s=round(ts[min(b, len(evs) - 1)] - ts[a]),  # wall clock from this stage's start to the next one's
                 **{k: kinds[a:b].count(k) for k in ("prompts", "nudges", "check_retries", "retries")})
    merged = []  # two log lines for one stage (e.g. "build: start", "build: done") are one row; a later return is rework
    for s in stages:
        if merged and merged[-1]["name"] == s["name"]:
            m = merged[-1]
            for k, v in s.items():
                if isinstance(v, (int, float)) and k != "avg_latency_s":
                    m[k] = m.get(k, 0) + v
            m["turn_ids"] = m.get("turn_ids", set()) | s.get("turn_ids", set())  # one turn can span both lines
        else:
            merged.append(s)
    for m in merged:  # sets don't serialise; keep the count
        if "turn_ids" in m:
            m["turns"] = len(m.pop("turn_ids"))
    return merged


USER_KINDS = [("Answer from the product owner", "prompts"), (NUDGE[:30], "nudges"),
              ("The factory's checks failed", "check_retries"), ("The previous turn was interrupted", "retries")]

def user_kind(e):
    """Classify a user message by the shell's own wording: a human answer, a nudge, check feedback, a retry or the brief."""
    if e["kind"] != "MessageEvent" or e.get("source") != "user":
        return None
    text = "".join(c.get("text", "") for c in e.get("llm_message", {}).get("content", []))
    return next((k for p, k in USER_KINDS if text.startswith(p)), "brief")


def step(rid, message):
    """One agent turn, then: park on a question, or check -> (feedback | PR)."""
    update(rid, lambda r: r.update(status="running", current_stage="agent"))
    event(rid, "agent_turn", message[:120])
    final, secs, stats = agent_turn(rid, message)
    def rec(r):
        r["stages"] = stages_from_log(rid)
        r.setdefault("turns", []).append({"ts": now(), "ended": time.time(), "seconds": secs, **stats, "final": final[-2000:]})
        if r["stages"] and "llm_calls" not in r["stages"][0]:  # no events (old runs): run totals on the last stage row
            tot = lambda k: sum(t.get(k, 0) for t in r["turns"])
            r["stages"][-1].update(duration_s=tot("seconds"), llm_calls=tot("llm_calls"),
                                   prompt_tokens=tot("prompt_tokens"), completion_tokens=tot("completion_tokens"))
    update(rid, rec)
    q = find_question(final)
    if q:
        def ask(r):
            r["questions"].append({"id": f"q{len(r['questions']) + 1}", "text": q, "blocking": True, "status": "open",
                                   "stage": (r["stages"][-1]["name"] if r["stages"] else "agent"),
                                   "stage_idx": len(r["stages"]) - 1, "asked_at": now()})
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
            update(rid, lambda r: r.update(status="failed", error=f"{type(e).__name__}: {e}"[-1500:], failed_at=time.time()))
            event(rid, "failed", str(e)[:200])
