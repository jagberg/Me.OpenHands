"""Activities: every side effect of the blueprint (git, gh, filesystem, LLM agent runs).

Deterministic steps (setup, tests, collect, PR) are plain code; only agent_stage calls the LLM.
All take the run id and cfg so they are independent of worker memory (Temporal can retry them on any worker).
"""
import fnmatch, json, os, subprocess, time
from datetime import datetime
from pathlib import Path

from temporalio import activity

os.environ.setdefault("OPENHANDS_SUPPRESS_BANNER", "1")

HERE = Path(__file__).resolve().parent
DATA = Path(os.environ.get("DATA_DIR", HERE.parent / "runs"))
SKILLS = HERE / "skills"
# LLM: Ollama now; Bedrock later = LLM_MODEL=bedrock/<model-id>, LLM_BASE_URL="", AWS creds via env/role. No code change.
MODEL = os.environ.get("LLM_MODEL", "ollama_chat/qwen3-14b-oh")
BASE_URL = os.environ.get("LLM_BASE_URL", "http://localhost:11434") or None
API_KEY = os.environ.get("LLM_API_KEY", "ollama" if MODEL.startswith("ollama") else "") or None  # "ollama" is a dummy; Ollama ignores it
GIT_BASE = os.environ.get("GIT_BASE", "git@github.com:")  # container: https://github.com/ + GH_TOKEN


def sh(cmd, cwd=None, check=True, timeout=300):
    r = subprocess.run(cmd, cwd=cwd, shell=isinstance(cmd, str), capture_output=True, text=True, timeout=timeout)
    if check and r.returncode:
        raise RuntimeError(f"{cmd!r} failed ({r.returncode}):\n{r.stdout}\n{r.stderr}")
    return r


def ws(rid): return DATA / rid / "workspace"
def wd(rid, cfg): return ws(rid) / cfg["workdir"]


def _tests(rid, cfg):
    r = sh(cfg["test_cmd"], cwd=wd(rid, cfg), check=False)
    return {"passed": r.returncode == 0, "output": (r.stdout + r.stderr)[-1500:]}


@activity.defn
def write_run(state: dict) -> None:
    """Dashboard reads runs/<id>/run.json; Temporal history stays the source of truth."""
    p = DATA / state["id"] / "run.json"
    p.parent.mkdir(parents=True, exist_ok=True)
    tmp = p.with_suffix(".tmp")
    tmp.write_text(json.dumps(state, indent=2))
    tmp.replace(p)


@activity.defn
def setup_workspace(rid: str, cfg: dict) -> dict:
    w = ws(rid)
    if not (w / ".git").exists():  # idempotent on retry
        sh(["git", "clone", "-q", "--depth", "1", f"{GIT_BASE}{cfg['repo']}.git", str(w)])
        sh(["git", "config", "user.name", "OpenHands (blueprint)"], cwd=w)
        sh(["git", "config", "user.email", "openhands@localhost"], cwd=w)
        base = sh(["git", "rev-parse", "--abbrev-ref", "HEAD"], cwd=w).stdout.strip()
        if cfg.get("throwaway_base"):  # PR targets a copy of the default branch, so merging never changes it
            base = f"ai-eval/base-{rid}"
            sh(["git", "checkout", "-q", "-b", base], cwd=w)
        sh(["git", "checkout", "-q", "-b", f"ai/{rid}"], cwd=w)
        (w / ".git" / "info" / "base").write_text(base)
    return {"base_branch": (w / ".git" / "info" / "base").read_text(), "head_branch": f"ai/{rid}",
            "tests": _tests(rid, cfg), "model": MODEL}


@activity.defn
def agent_stage(rid: str, name: str, cfg: dict, ctx: dict) -> dict:
    """One OpenHands conversation for one skill. Metrics come from the SDK."""
    # ponytail: no heartbeat; a dead worker is only noticed at start_to_close (40 min). Add heartbeats via a callback if runs get long.
    from openhands.sdk import LLM, Agent, AgentContext, Conversation
    from openhands.sdk.conversation.response_utils import get_agent_final_response
    from openhands.sdk.event import ActionEvent
    from openhands.tools.preset.default import get_default_tools

    kw = dict(model=MODEL, base_url=BASE_URL, api_key=API_KEY, timeout=900, num_retries=2, max_output_tokens=4096,
              native_tool_calling=True, usage_id="agent")
    if MODEL.startswith("ollama"):
        kw.update(reasoning_effort="none", max_input_tokens=32768, litellm_extra_body={"options": {"num_ctx": 32768}})
    agent = Agent(llm=LLM(**kw), tools=get_default_tools(enable_browser=False)[:2],  # terminal + file_editor
                  agent_context=AgentContext(load_user_skills=False, load_public_skills=False))
    actions = []
    conv = Conversation(agent=agent, workspace=str(ws(rid)), visualizer=None, max_iteration_per_run=40,
                        callbacks=[lambda e: actions.append(e) if isinstance(e, ActionEvent) else None])
    prompt = (f"{(SKILLS / f'{name}.md').read_text()}\n\n## Context\nWorking folder: {cfg['workdir']} (relative to cwd).\n"
              f"Test command (run inside that folder): `{cfg['test_cmd']}`\n{ctx.get('extra', '')}\n"
              f"## Decisions so far\n{ctx['decisions']}\n## Open questions (proceed with your stated assumption)\n{ctx['open']}\n\n"
              f"## Ticket\n{ctx['title']}\n{ctx['brief']}")
    rec = {"name": name, "status": "running", "started": datetime.now().isoformat(timespec="seconds")}
    t0 = time.time()
    try:
        conv.send_message(prompt)
        conv.run()
        rec["status"] = "done"
        rec["final_message"] = get_agent_final_response(conv.state.events)
    except Exception as e:
        rec["status"] = "error"
        rec["error"] = f"{type(e).__name__}: {e}"
    m = conv.conversation_stats.get_combined_metrics()
    u = m.accumulated_token_usage
    lat = [x.latency for x in m.response_latencies]
    rec.update(duration_s=round(time.time() - t0, 1), llm_calls=len(lat), prompt_tokens=getattr(u, "prompt_tokens", 0),
               completion_tokens=getattr(u, "completion_tokens", 0), avg_latency_s=round(sum(lat) / len(lat), 1) if lat else 0,
               cost_usd=m.accumulated_cost, tool_calls=len(actions), tools=sorted({a.tool_name for a in actions}))
    conv.close()
    return rec


@activity.defn
def harvest_question(rid: str, cfg: dict) -> dict | None:
    """Agents ask a human by writing .ignite/QUESTION.md (BLOCKING: or ASK: + ASSUMPTION:)."""
    f = wd(rid, cfg) / ".ignite" / "QUESTION.md"
    if not f.exists():
        return None
    lines = [l.strip() for l in f.read_text().splitlines() if l.strip()]
    f.unlink()
    if not lines:
        return None
    return {"text": lines[0].split(":", 1)[-1].strip(), "blocking": lines[0].upper().startswith("BLOCKING"),
            "assumption": next((l.split(":", 1)[1].strip() for l in lines if l.upper().startswith("ASSUMPTION")), "")}


@activity.defn
def decision_gate(rid: str, cfg: dict, ctx: dict) -> dict:
    """One narrow LLM call (not an agent loop): list decisions a human must make, as JSON.
    Weak models skip free-form 'ask a human' instructions; a structured extraction step is reliable."""
    import re
    import litellm

    brief = wd(rid, cfg) / ".ignite" / "brief.md"
    prompt = ("List the decisions in this ticket that a human must make before implementation: anything the ticket says to "
              "ask a human about, or a genuinely ambiguous behaviour choice. Ignore things the ticket already decides.\n"
              'Reply with ONLY a JSON array: [{"question": "...", "options": ["...", "..."], "assumption": "your default"}]. '
              "Reply [] if there are none.\n\n"
              f"## Ticket\n{ctx['title']}\n{ctx['brief']}\n\n## Brief\n{brief.read_text() if brief.exists() else '(none)'}")
    t0 = time.time()
    kw = {"api_base": BASE_URL, "api_key": API_KEY} if MODEL.startswith("ollama") else {}
    if MODEL.startswith("ollama"):
        kw["extra_body"] = {"options": {"num_ctx": 32768}, "think": False}
    r = litellm.completion(model=MODEL, messages=[{"role": "user", "content": prompt}], temperature=0, timeout=600, **kw)
    text = r.choices[0].message.content or ""
    m = re.search(r"\[.*\]", re.sub(r"<think>.*?</think>", "", text, flags=re.S), re.S)
    try:
        items = json.loads(m.group(0)) if m else []
    except ValueError:
        items = []
    qs = [{"text": i["question"] + (f" Options: {' / '.join(i['options'])}" if i.get("options") else ""),
           "assumption": i.get("assumption", ""), "blocking": True} for i in items if isinstance(i, dict) and i.get("question")]
    u = r.usage
    rec = {"name": "decision-gate", "status": "done", "duration_s": round(time.time() - t0, 1), "llm_calls": 1,
           "prompt_tokens": u.prompt_tokens, "completion_tokens": u.completion_tokens, "avg_latency_s": round(time.time() - t0, 1),
           "cost_usd": 0.0, "tool_calls": 0, "final_message": f"{len(qs)} decision(s) for a human"}
    return {"rec": rec, "questions": qs}


@activity.defn
def decision_tests(rid: str, cfg: dict) -> int:
    """Count test functions in test_decisions.py: each human decision must be pinned by a test."""
    f = wd(rid, cfg) / "test_decisions.py"
    return f.read_text().count("def test_") if f.exists() else 0


@activity.defn
def run_tests(rid: str, cfg: dict) -> dict:
    return _tests(rid, cfg)


@activity.defn
def collect(rid: str, cfg: dict) -> dict:
    w, d = ws(rid), cfg["workdir"]
    changed = sh(["git", "status", "--porcelain", "--", d], cwd=w).stdout.splitlines()
    touched = [l[3:] for l in changed if any(fnmatch.fnmatch(Path(l[3:]).name, g) for g in cfg.get("protected", []))]
    sh(["git", "add", "-A", "--", d], cwd=w)
    patch = sh(["git", "diff", "--cached", "--", d, f":(exclude){d}/.ignite" if d != "." else ":(exclude).ignite"], cwd=w).stdout
    ign = wd(rid, cfg) / ".ignite"
    tests = _tests(rid, cfg)
    return {"tests": tests, "diff": {"patch": patch},
            "artifacts": {p.stem: p.read_text() for p in sorted(ign.glob("*.md"))} if ign.exists() else {},
            "checks": {"tests_pass_after": tests["passed"], "protected_files_untouched": not touched, "has_changes": bool(patch.strip())}}


@activity.defn
def open_pr(rid: str, cfg: dict, s: dict) -> str:
    w = ws(rid)
    head = s["head_branch"]
    found = sh(["gh", "pr", "list", "--repo", cfg["repo"], "--head", head, "--json", "url", "-q", ".[0].url"], cwd=w, check=False).stdout.strip()
    if found:  # retry after a partial success
        return found
    if sh(["git", "status", "--porcelain"], cwd=w).stdout.strip():
        sh(["git", "add", "-A"], cwd=w)
        sh(["git", "commit", "-q", "-m", f"fix: {s['title']}\n\nAuthored by OpenHands (Temporal blueprint).\n\nCo-Authored-By: OpenHands <openhands@all-hands.dev>"], cwd=w)
    if s["base_branch"].startswith("ai-eval/"):
        sh(["git", "push", "-q", "origin", s["base_branch"]], cwd=w)
    sh(["git", "push", "-q", "origin", head], cwd=w)
    tot = lambda k: sum(x.get(k) or 0 for x in s["stages"])
    open_q = [q for q in s["questions"] if q["status"] == "open"]
    answered = [q for q in s["questions"] if q["status"] == "answered"]
    body = (f"## Summary\n{s['summary']}\n\n## Ticket\n{s['title']} (source: {s['source']})\n\n"
            "## Validation\n| Check | Result |\n|---|---|\n"
            + "".join(f"| {k} | {'✅' if v else '❌'} |\n" for k, v in s["checks"].items())
            + f"\n## Lifecycle\n- stages: {' → '.join(x['name'] for x in s['stages'])}\n"
            f"- {tot('llm_calls')} LLM calls, {tot('prompt_tokens')} in / {tot('completion_tokens')} out tokens, model `{s['model']}`\n"
            + ("\n## Human decisions\n" + "".join(f"- {q['text']} → **{q['answer']}**\n" for q in answered) if answered else "")
            + ("\n## Open questions (agent proceeded on its assumption)\n" + "".join(f"- {q['text']} (assumed: {q['assumption']})\n" for q in open_q) if open_q else "")
            + f"\nTemporal workflow: `{rid}`. AI review follows as a comment; a human makes the final review and merges.\n\n🤖 Generated with OpenHands (Temporal blueprint)")
    out = sh(["gh", "pr", "create", "--repo", cfg["repo"], "--base", s["base_branch"], "--head", head,
              "--title", f"{s['title']} [{rid}]", "--body", body], cwd=w).stdout.strip()
    return out.splitlines()[-1]


@activity.defn
def post_review(rid: str, cfg: dict, pr_url: str, model: str) -> str:
    f = wd(rid, cfg) / ".ignite" / "ai-review.md"
    if not f.exists():
        return ""
    text = f.read_text()
    sh(["gh", "pr", "comment", pr_url, "--body", f"🤖 **AI review** (OpenHands, `{model}`)\n\n{text}"])
    return text


@activity.defn
def pr_state(pr_url: str) -> str:
    return sh(["gh", "pr", "view", pr_url, "--json", "state", "-q", ".state"]).stdout.strip()


ALL = [write_run, setup_workspace, agent_stage, harvest_question, decision_gate, decision_tests, run_tests, collect, open_pr, post_review, pr_state]
