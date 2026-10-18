"""The blueprint: a fixed sequence of deterministic and agent nodes (Stripe-style), with human gates.

ticket -> setup* -> brief -> plan -> build (+ tests*, 1 retry) -> eng/sec/qa reviews -> collect* -> PR* -> AI review -> human review -> merged
(* = deterministic). Any agent may ask a human; BLOCKING questions park the workflow until the `answer` signal.
"""
import asyncio
from datetime import timedelta

from temporalio import workflow
from temporalio.common import RetryPolicy
from temporalio.exceptions import ApplicationError

with workflow.unsafe.imports_passed_through():
    import activities as a

PLAN = ["ignite-brief", "ignite-plan"]
BUILD = "ignite-build"
REVIEWS = ["engineering-review", "security-review", "qa-review"]
AI_REVIEW = "ai-code-review"
TASK_QUEUE = "ignite"


@workflow.defn
class IgniteBlueprint:
    def __init__(self) -> None:
        self.s: dict = {}

    # ---- human in the loop ----
    @workflow.signal
    async def answer(self, qid: str, text: str) -> None:
        q = next((q for q in self.s.get("questions", []) if q["id"] == qid), None)
        if not q or q["status"] != "open":
            return
        q.update(status="answered", answer=text, answered_at=self.now())
        await self.save("answered", f"{qid}: {text[:120]}")

    @workflow.query
    def state(self) -> dict:
        return self.s

    # ---- helpers ----
    def now(self) -> str:
        return workflow.now().isoformat(timespec="seconds")

    async def act(self, fn, *args, minutes=5, attempts=3):
        return await workflow.execute_activity(fn, args=list(args), start_to_close_timeout=timedelta(minutes=minutes),
                                               retry_policy=RetryPolicy(maximum_attempts=attempts))

    async def save(self, kind: str | None = None, msg: str = "") -> None:
        if kind:
            self.s["events"].append({"ts": self.now(), "kind": kind, "msg": msg})
        await self.act(a.write_run, self.s, minutes=1)

    def ctx(self, extra: str = "") -> dict:
        qs = self.s["questions"]
        return {"title": self.s["title"], "brief": self.s["problem"], "extra": extra,
                "decisions": "\n".join(f"- {q['text']} -> {q['answer']}" for q in qs if q["status"] == "answered") or "none",
                "open": "\n".join(f"- {q['text']} (assumed: {q['assumption']})" for q in qs if q["status"] == "open") or "none"}

    async def stage(self, name: str, extra: str = "") -> dict:
        while True:
            self.s.update(current_stage=name)
            self.s["stages"].append({"name": name, "status": "running", "started": self.now()})
            await self.save()
            rec = await self.act(a.agent_stage, self.rid, name, self.cfg, self.ctx(extra), minutes=40, attempts=2)
            self.s["stages"][-1] = rec
            if rec["status"] != "done":
                raise ApplicationError(f"stage {name} failed: {rec.get('error')}", non_retryable=True)
            q = await self.act(a.harvest_question, self.rid, self.cfg)
            if q and not any(x["text"] == q["text"] for x in self.s["questions"]):
                q.update(id=f"q{len(self.s['questions']) + 1}", stage=name, status="open", asked_at=self.now())
                self.s["questions"].append(q)
                await self.save("question", f"{'BLOCKING ' if q['blocking'] else ''}{q['id']} from {name}: {q['text']}")
                if q["blocking"]:
                    self.s["status"] = "awaiting_decision"
                    await self.save()
                    await workflow.wait_condition(lambda: q["status"] == "answered")
                    self.s["status"] = "running"
                    await self.save("resumed", f"{name} reruns with the decision")
                    continue  # rerun this stage with the decision in context
            await self.save()
            return rec

    async def decision_gate(self) -> None:
        """Human gate after the brief: extracted decisions become blocking questions; plan waits for all answers."""
        self.s.update(current_stage="decision-gate")
        res = await self.act(a.decision_gate, self.rid, self.cfg, self.ctx(), minutes=15, attempts=2)
        self.s["stages"].append(res["rec"])
        new = [q for q in res["questions"] if not any(x["text"] == q["text"] for x in self.s["questions"])]
        for q in new:
            q.update(id=f"q{len(self.s['questions']) + 1}", stage="decision-gate", status="open", asked_at=self.now())
            self.s["questions"].append(q)
            await self.save("question", f"BLOCKING {q['id']}: {q['text']}")
        if new:
            self.s["status"] = "awaiting_decision"
            await self.save()
            await workflow.wait_condition(lambda: all(q["status"] == "answered" for q in new))
            self.s["status"] = "running"
            await self.save("resumed", "all decisions answered; planning continues")
        else:
            await self.save()

    # ---- the blueprint ----
    @workflow.run
    async def run(self, inp: dict) -> dict:
        self.rid, self.cfg = workflow.info().workflow_id, inp["cfg"]
        self.s = {"id": self.rid, "title": inp["title"], "problem": inp["brief"], "source": inp.get("source", "manual"),
                  "repo": self.cfg["repo"], "status": "running", "created": self.now(), "started": self.now(),
                  "current_stage": "setup", "stages": [], "questions": [], "events": [], "pr_url": None, "pr_state": None,
                  "tests": {}, "checks": {}, "diff": {}, "artifacts": {}, "summary": "", "error": None, "engine": "temporal"}
        try:
            await self.save("started", f"ticket from {self.s['source']}: {inp['title']}")
            setup = await self.act(a.setup_workspace, self.rid, self.cfg)
            self.s.update(base_branch=setup["base_branch"], head_branch=setup["head_branch"], model=setup["model"])
            self.s["tests"]["before"] = setup["tests"]
            if workflow.patched("decision-gate"):  # versioning: runs started before the gate existed replay the old path
                await self.stage(PLAN[0])  # ignite-brief
                await self.decision_gate()
                for n in PLAN[1:]:
                    await self.stage(n)
            else:
                for n in PLAN:
                    await self.stage(n)

            feedback = ""
            pin = workflow.patched("decision-tests")  # versioning guard for runs started before this check
            decided = [q for q in self.s["questions"] if q["status"] == "answered"]
            pinned = None
            for attempt in ((1, 2, 3) if pin else (1, 2)):  # deterministic gate around the agentic build, bounded retries
                build = await self.stage(BUILD, feedback)
                t = await self.act(a.run_tests, self.rid, self.cfg)
                pinned = await self.act(a.decision_tests, self.rid, self.cfg) if pin and decided else None
                if t["passed"] and (pinned is None or pinned >= len(decided)):
                    break
                feedback = ("" if t["passed"] else f"The test command fails after your change. Output:\n{t['output']}\n") + (
                    f"test_decisions.py has {pinned} test(s) but there are {len(decided)} human decision(s); "
                    "add one test per decision and implement it.\n" if pinned is not None and pinned < len(decided) else "")
                await self.save("build_rejected", f"build attempt {attempt}: " + feedback.splitlines()[0][:150])
            self.s["summary"] = build.get("final_message", "")

            for n in REVIEWS:
                await self.stage(n)

            c = await self.act(a.collect, self.rid, self.cfg)
            self.s["tests"]["after"] = c["tests"]
            if pinned is not None:
                c["checks"]["decisions_pinned_by_tests"] = pinned >= len(decided)
            self.s.update(checks=c["checks"], diff=c["diff"], artifacts=c["artifacts"], current_stage="pr")
            await self.save("validated", str(c["checks"]))
            if not all(c["checks"].values()):
                raise ApplicationError(f"validation failed: {c['checks']}", non_retryable=True)

            url = await self.act(a.open_pr, self.rid, self.cfg, self.s, attempts=2)
            self.s.update(pr_url=url, pr_state="OPEN", pr_opened=self.now(), status="ai_review")
            await self.save("pr_opened", url)

            await self.stage(AI_REVIEW, f"Base branch for the diff: {self.s['base_branch']}")
            review = await self.act(a.post_review, self.rid, self.cfg, url, self.s["model"])
            if review:
                self.s["artifacts"]["ai-review"] = review
            self.s.update(status="human_review", current_stage="human-review")
            await self.save("ready", f"ready for human review: {url}")

            while True:  # final gate: a human merges or closes the PR
                st = await self.act(a.pr_state, url, minutes=1)
                if st in ("MERGED", "CLOSED"):
                    break
                # ponytail: 60s poll = ~1.4k timer events/day of history; switch to a GitHub webhook -> signal if PRs sit for weeks
                await asyncio.sleep(60)
            self.s.update(status=st.lower(), pr_state=st, finished=self.now(), current_stage=None)
            await self.save(st.lower(), f"PR {st.lower()}")
        except Exception as e:
            self.s.update(status="failed", error=str(e)[-1500:], finished=self.now())
            await self.save("failed", str(e)[:300])
            raise ApplicationError(str(e)[-1500:], non_retryable=True)
        await workflow.wait_condition(workflow.all_handlers_finished)
        return {"status": self.s["status"], "pr_url": self.s["pr_url"]}
