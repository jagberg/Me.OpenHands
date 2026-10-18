"""The blueprint (v2): a fixed sequence of deterministic and agent nodes (Stripe-style), with human gates.

ticket -> setup* -> brief -> decision gate -> [HUMAN] -> plan -> build -> tests* + decision tests* (max 3)
       -> eng/sec/qa reviews -> validate* -> PR* -> AI review -> [HUMAN merges/closes] -> done      (* = deterministic)

State lives only in Temporal: the dashboard reads it with the `state` query (running) or the result (finished).
The Temporal UI shows a live "Issue & resolution" summary via current details, and each activity is labelled.
"""
import re
from datetime import timedelta

from temporalio import workflow
from temporalio.common import RetryPolicy
from temporalio.exceptions import ApplicationError

with workflow.unsafe.imports_passed_through():
    import activities as a

BRIEF, PLAN, BUILD, AI_REVIEW = "ignite-brief", "ignite-plan", "ignite-build", "ai-code-review"
REVIEWS = ["engineering-review", "security-review", "qa-review"]
TASK_QUEUE = "ignite"


@workflow.defn(name="IgniteBlueprintV2")
class IgniteBlueprint:
    def __init__(self) -> None:
        self.s: dict = {}

    # ---- human in the loop ----
    @workflow.signal
    def answer(self, qid: str, text: str) -> None:
        q = next((q for q in self.s.get("questions", []) if q["id"] == qid), None)
        if q and q["status"] == "open":
            q.update(status="answered", answer=text, answered_at=self.now())
            self.mark("answered", f"{qid}: {text[:120]}")

    @workflow.query
    def state(self) -> dict:
        return self.s

    # ---- helpers ----
    def now(self) -> str:
        return workflow.now().isoformat(timespec="seconds")

    async def act(self, fn, *args, summary: str, minutes=5, attempts=3):
        return await workflow.execute_activity(fn, args=list(args), summary=summary, start_to_close_timeout=timedelta(minutes=minutes),
                                               retry_policy=RetryPolicy(maximum_attempts=attempts))

    def mark(self, kind: str | None = None, msg: str = "") -> None:
        """Record an event and refresh the summary shown in the Temporal UI. No activity, so no history cost."""
        if kind:
            self.s["events"].append({"ts": self.now(), "kind": kind, "msg": msg})
        workflow.set_current_details(self.details())

    def details(self) -> str:
        s, tot = self.s, lambda k: sum(x.get(k) or 0 for x in self.s["stages"])
        qs = "".join(f"- **{q['id']}** {q['text']} → " + (f"**{q['answer']}**\n" if q["status"] == "answered" else "⏳ *waiting for a human*\n")
                     for q in s["questions"])
        return (f"**Status:** {s['status']}" + (f" · stage `{s['current_stage']}`" if s.get("current_stage") else "") + "\n\n"
                f"### Issue\n{s['title']}\n\n"
                + (f"### Decisions\n{qs}\n" if qs else "")
                + (f"### Resolution\n{s['resolution']}\n\n" if s.get("resolution") else "")
                + (f"**PR:** {s['pr_url']}\n\n" if s.get("pr_url") else "")
                + f"### Metrics\n{len(s['stages'])} stages · {tot('llm_calls')} LLM calls · {tot('prompt_tokens'):,} in / "
                  f"{tot('completion_tokens'):,} out tokens · {round(tot('duration_s'))}s agent time")

    def ctx(self, extra: str = "") -> dict:
        qs = self.s["questions"]
        return {"title": self.s["title"], "brief": self.s["problem"], "extra": extra,
                "decisions": "\n".join(f"- {q['text']} -> {q['answer']}" for q in qs if q["status"] == "answered") or "none",
                "open": "\n".join(f"- {q['text']} (assumed: {q['assumption']})" for q in qs if q["status"] == "open") or "none"}

    def add_questions(self, qs: list, stage: str) -> list:
        new = [q for q in qs if not any(x["text"] == q["text"] for x in self.s["questions"])]
        for q in new:
            q.update(id=f"q{len(self.s['questions']) + 1}", stage=stage, status="open", asked_at=self.now())
            self.s["questions"].append(q)
            self.mark("question", f"{'BLOCKING ' if q['blocking'] else ''}{q['id']} from {stage}: {q['text']}")
        return new

    async def wait_for_humans(self, qs: list, why: str) -> None:
        self.s["status"] = "awaiting_decision"
        self.mark()
        await workflow.wait_condition(lambda: all(q["status"] == "answered" for q in qs))
        self.s["status"] = "running"
        self.mark("resumed", why)

    async def stage(self, name: str, extra: str = "") -> dict:
        while True:
            self.s.update(current_stage=name)
            self.s["stages"].append({"name": name, "status": "running", "started": self.now()})
            self.mark()
            rec = await self.act(a.agent_stage, self.rid, name, self.cfg, self.ctx(extra), summary=name, minutes=40, attempts=2)
            q = rec.pop("question", None)
            self.s["stages"][-1] = rec
            if rec["status"] != "done":
                raise ApplicationError(f"stage {name} failed: {rec.get('error')}", non_retryable=True)
            new = self.add_questions([q] if q else [], name)
            if any(x["blocking"] for x in new):
                await self.wait_for_humans(new, f"{name} reruns with the decision")
                continue  # rerun this stage with the decision in context
            self.mark()
            return rec

    def resolution(self, build: dict, c: dict) -> str:
        """Deterministic 'how it was solved' summary from what the run produced."""
        # last PASS/CONCERNS token wins; models sometimes emit literal "\n" so don't rely on line structure
        verdict = lambda k: (re.findall(r"\b(PASS|CONCERNS)\b", c["artifacts"].get(k, "")) or ["n/a"])[-1]
        files = sorted({l[6:] for l in c["diff"]["patch"].splitlines() if l.startswith("+++ b/")})
        decided = "".join(f"- {q['text']} → **{q['answer']}**\n" for q in self.s["questions"] if q["status"] == "answered")
        return (f"{build.get('final_message', '').strip()}\n\n"
                f"**Files changed:** {', '.join(f'`{f}`' for f in files) or 'none'}\n\n"
                + (f"**Human decisions applied:**\n{decided}\n" if decided else "")
                + "**Checks:** " + " · ".join(f"{'✅' if v else '❌'} {k.replace('_', ' ')}" for k, v in c["checks"].items()) + "\n\n"
                f"**Reviews:** security {verdict('security')} · QA {verdict('qa')}")

    # ---- the blueprint ----
    @workflow.run
    async def run(self, inp: dict) -> dict:
        self.rid, self.cfg = workflow.info().workflow_id, inp["cfg"]
        self.s = {"id": self.rid, "title": inp["title"], "problem": inp["brief"], "source": inp.get("source", "manual"),
                  "repo": self.cfg["repo"], "status": "running", "created": self.now(), "started": self.now(),
                  "current_stage": "setup", "stages": [], "questions": [], "events": [], "pr_url": None, "pr_state": None,
                  "tests": {}, "checks": {}, "diff": {}, "artifacts": {}, "summary": "", "resolution": "", "error": None,
                  "engine": "temporal"}
        try:
            self.mark("started", f"ticket from {self.s['source']}: {inp['title']}")
            setup = await self.act(a.setup_workspace, self.rid, self.cfg, summary="setup workspace")
            self.s.update(base_branch=setup["base_branch"], head_branch=setup["head_branch"], model=setup["model"])
            self.s["tests"]["before"] = setup["tests"]

            await self.stage(BRIEF)
            self.s["current_stage"] = "decision-gate"
            gate = await self.act(a.decision_gate, self.rid, self.cfg, self.ctx(), summary="decision gate", minutes=15, attempts=2)
            self.s["stages"].append(gate["rec"])
            new = self.add_questions(gate["questions"], "decision-gate")
            if new:
                await self.wait_for_humans(new, "all decisions answered; planning continues")
            await self.stage(PLAN)

            feedback, pinned = "", None
            decided = [q for q in self.s["questions"] if q["status"] == "answered"]
            for attempt in (1, 2, 3):  # deterministic gate around the agentic build, bounded retries
                build = await self.stage(BUILD, feedback)
                t = await self.act(a.run_tests, self.rid, self.cfg, summary="run tests")
                pinned = await self.act(a.decision_tests, self.rid, self.cfg, summary="check decision tests") if decided else None
                if t["passed"] and (pinned is None or pinned >= len(decided)):
                    break
                feedback = ("" if t["passed"] else f"The test command fails after your change. Output:\n{t['output']}\n") + (
                    f"test_decisions.py has {pinned} test(s) but there are {len(decided)} human decision(s); "
                    "add one test per decision and implement it.\n" if pinned is not None and pinned < len(decided) else "")
                self.mark("build_rejected", f"build attempt {attempt}: " + feedback.splitlines()[0][:150])
            self.s["summary"] = build.get("final_message", "")

            for n in REVIEWS:
                await self.stage(n)

            c = await self.act(a.collect, self.rid, self.cfg, summary="validate")
            if pinned is not None:
                c["checks"]["decisions_pinned_by_tests"] = pinned >= len(decided)
            self.s["tests"]["after"] = c["tests"]
            self.s.update(checks=c["checks"], diff=c["diff"], artifacts=c["artifacts"], current_stage="pr",
                          resolution=self.resolution(build, c))
            self.mark("validated", str(c["checks"]))
            if not all(c["checks"].values()):
                raise ApplicationError(f"validation failed: {c['checks']}", non_retryable=True)

            url = await self.act(a.open_pr, self.rid, self.cfg, self.s, summary="open PR", attempts=2)
            self.s.update(pr_url=url, pr_state="OPEN", pr_opened=self.now(), status="ai_review")
            self.mark("pr_opened", url)

            await self.stage(AI_REVIEW, f"Base branch for the diff: {self.s['base_branch']}")
            review = await self.act(a.post_review, self.rid, self.cfg, url, self.s["model"], summary="post AI review")
            if review:
                self.s["artifacts"]["ai-review"] = review
            self.s.update(status="human_review", current_stage="human-review")
            self.mark("ready", f"ready for human review: {url}")

            delay = 60
            while True:  # final gate: a human merges or closes the PR
                st = await self.act(a.pr_state, url, summary="check PR state", minutes=1)
                if st in ("MERGED", "CLOSED"):
                    break
                # ponytail: backoff poll (1m -> 15m cap, ~100 checks/day); a GitHub webhook -> signal removes polling in production
                await workflow.sleep(timedelta(seconds=delay), summary="waiting for human PR review")
                delay = min(delay * 2, 900)
            self.s.update(status=st.lower(), pr_state=st, finished=self.now(), current_stage=None)
            self.mark(st.lower(), f"PR {st.lower()}")
        except Exception as e:
            self.s.update(status="failed", error=str(e)[-1500:], finished=self.now())
            self.mark("failed", str(e)[:300])
            raise ApplicationError(str(e)[-1500:], non_retryable=True)
        return self.s
