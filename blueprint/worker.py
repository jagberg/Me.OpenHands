"""Temporal worker + small client helpers used by start.py and the dashboard.

  .venv/bin/python worker.py                      # run the worker
"""
import asyncio, os, sys
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime

from temporalio.client import Client
from temporalio.worker import Worker

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import activities
import workflow_v1
from workflow import TASK_QUEUE, IgniteBlueprint

ADDRESS = os.environ.get("TEMPORAL_ADDRESS", "localhost:7233")
# The trial repo; PRs target a throwaway copy of main so merging never changes the test case.
DEFAULT_CFG = {"repo": "jagberg/ai-agent-trial-sandbox", "workdir": ".", "test_cmd": "uv run --with pytest pytest -q",
               "protected": ["test_calc.py"], "throwaway_base": True}


async def start(title: str, brief: str, source: str = "manual", cfg: dict | None = None) -> str:
    client = await Client.connect(ADDRESS)
    wid = "ignite-" + datetime.now().strftime("%Y%m%d-%H%M%S")
    await client.start_workflow(IgniteBlueprint.run, {"title": title, "brief": brief, "source": source, "cfg": cfg or DEFAULT_CFG},
                                id=wid, task_queue=TASK_QUEUE, static_summary=title, static_details=brief[:4000])
    return wid


async def answer(wid: str, qid: str, text: str) -> None:
    client = await Client.connect(ADDRESS)
    await client.get_workflow_handle(wid).signal("answer", args=[qid, text])  # by name: works for v1 and v2


_done: dict = {}  # finished v2 runs never change; cache their results


async def runs() -> list:
    """v2 run states straight from Temporal: query while running, result once finished."""
    client = await Client.connect(ADDRESS)
    out = []
    async for w in client.list_workflows('WorkflowType="IgniteBlueprintV2"'):
        if w.id in _done:
            out.append(_done[w.id]); continue
        h = client.get_workflow_handle(w.id, run_id=w.run_id)
        try:
            if w.status and w.status.name == "RUNNING":
                out.append(await h.query(IgniteBlueprint.state))
            else:
                try:
                    _done[w.id] = await h.result()
                except Exception:  # failed runs: last state via query (needs the worker up)
                    _done[w.id] = await h.query(IgniteBlueprint.state)
                out.append(_done[w.id])
        except Exception as e:
            out.append({"id": w.id, "title": w.id, "status": "unknown", "engine": "temporal", "started": w.start_time.isoformat(),
                        "error": f"state unavailable (is the worker running?): {e}"})
    return out


async def main():
    client = await Client.connect(ADDRESS)
    # ponytail: one agent activity at a time - a local 14B model can't serve two; raise with a hosted model (Bedrock)
    worker = Worker(client, task_queue=TASK_QUEUE, workflows=[IgniteBlueprint, workflow_v1.IgniteBlueprint], activities=activities.ALL,
                    activity_executor=ThreadPoolExecutor(4), max_concurrent_activities=int(os.environ.get("MAX_ACTIVITIES", "2")))
    print(f"worker on {ADDRESS}, queue {TASK_QUEUE}, model {activities.MODEL}", flush=True)
    await worker.run()


if __name__ == "__main__":
    asyncio.run(main())
