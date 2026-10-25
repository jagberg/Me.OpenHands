"""Per-stage metrics from synthetic OpenHands events (no Docker, no model). Run: .venv/bin/python test_metrics.py"""
import json, tempfile
from pathlib import Path

import shell

shell.RUNS = Path(tempfile.mkdtemp())
ev = shell.RUNS / "r" / "conversations" / "c" / "events"; ev.mkdir(parents=True)
(shell.RUNS / "r" / "repo" / ".ignite").mkdir(parents=True)
(shell.RUNS / "r" / "repo" / ".ignite" / "log.md").write_text("brief: draft\nplan: propose\nplan: done\n")
stats = lambda p, c: {"kind": "ConversationStateUpdateEvent", "key": "stats",
                      "value": {"usage_to_metrics": {"agent": {"accumulated_token_usage": {"prompt_tokens": p, "completion_tokens": c}}}}}
user = lambda text: {"kind": "MessageEvent", "source": "user", "llm_message": {"content": [{"type": "text", "text": text}]}}
events = [  # (seconds, event)
    (0, user("Ticket: add median")),
    (10, {"kind": "ActionEvent", "source": "agent", "llm_response_id": "a", "cmd": "echo 'brief: draft' >> .ignite/log.md"}),
    (11, stats(100, 10)),
    (20, {"kind": "ActionEvent", "source": "agent", "llm_response_id": "b", "cmd": "cat docs/spec.md"}),
    (21, stats(250, 20)),
    (500, user("Answer from the product owner: approve")),  # human answer after a 479 s wait: not agent time
    (530, {"kind": "ActionEvent", "source": "agent", "llm_response_id": "c", "cmd": "echo 'plan: propose' >> .ignite/log.md"}),
    (531, stats(400, 35)),
    (540, user(shell.NUDGE)),  # nudge: same shell turn
    (550, {"kind": "ActionEvent", "source": "agent", "llm_response_id": "d", "cmd": "echo 'plan: done' >> .ignite/log.md"}),
    (551, stats(500, 40)),
    (600, user("Answer from the product owner: design ok")),
    (610, {"kind": "ActionEvent", "source": "agent", "llm_response_id": "e", "cmd": "ls"}),
    (611, stats(600, 45)),
]
for n, (t, e) in enumerate(events):
    e.update(timestamp=f"2026-10-24T00:{t // 60:02d}:{t % 60:02d}")
    (ev / f"event-{n:05d}.json").write_text(json.dumps(e))

brief, plan = shell.stages_from_log("r")  # the two plan lines merge into one row
assert (brief["llm_calls"], brief["tool_calls"], brief["prompt_tokens"], brief["completion_tokens"]) == (2, 2, 250, 20), brief
assert brief["duration_s"] == 21, brief  # 0..21 s of work; the 21..500 s wait ends in a user message
assert (brief["turns"], brief["prompts"], brief["wait_s"], brief["lead_s"]) == (1, 1, 479, 530), brief
assert (plan["llm_calls"], plan["prompt_tokens"], plan["completion_tokens"]) == (3, 350, 25), plan
assert (plan["turns"], plan["prompts"], plan["nudges"], plan["wait_s"]) == (2, 1, 1, 49), plan

# nudge decision: a plain agent message mid-process gets nudged; the finish tool does not
class MessageEvent:
    def __init__(self, source): self.source = source
class ActionEvent:
    def __init__(self, tool): self.source, self.tool_name = "agent", tool
assert shell.ended_on_text([ActionEvent("terminal"), MessageEvent("agent"), MessageEvent("user")])
assert not shell.ended_on_text([MessageEvent("agent"), ActionEvent("finish")])
assert not shell.ended_on_text([])
print("ok")
