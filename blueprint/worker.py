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
from workflow import TASK_QUEUE, IgniteBlueprint

ADDRESS = os.environ.get("TEMPORAL_ADDRESS", "localhost:7233")
# The trial repo; PRs target a throwaway copy of main so merging never changes the test case.
DEFAULT_CFG = {"repo": "jagberg/ai-agent-trial-sandbox", "workdir": ".", "test_cmd": "uv run --with pytest pytest -q",
               "protected": ["test_calc.py"], "throwaway_base": True}


async def start(title: str, brief: str, source: str = "manual", cfg: dict | None = None) -> str:
    client = await Client.connect(ADDRESS)
    wid = "ignite-" + datetime.now().strftime("%Y%m%d-%H%M%S")
    await client.start_workflow(IgniteBlueprint.run, {"title": title, "brief": brief, "source": source, "cfg": cfg or DEFAULT_CFG},
                                id=wid, task_queue=TASK_QUEUE)
    return wid


async def answer(wid: str, qid: str, text: str) -> None:
    client = await Client.connect(ADDRESS)
    await client.get_workflow_handle(wid).signal(IgniteBlueprint.answer, args=[qid, text])


async def main():
    client = await Client.connect(ADDRESS)
    # ponytail: one agent activity at a time - a local 14B model can't serve two; raise with a hosted model (Bedrock)
    worker = Worker(client, task_queue=TASK_QUEUE, workflows=[IgniteBlueprint], activities=activities.ALL,
                    activity_executor=ThreadPoolExecutor(4), max_concurrent_activities=int(os.environ.get("MAX_ACTIVITIES", "2")))
    print(f"worker on {ADDRESS}, queue {TASK_QUEUE}, model {activities.MODEL}", flush=True)
    await worker.run()


if __name__ == "__main__":
    asyncio.run(main())
