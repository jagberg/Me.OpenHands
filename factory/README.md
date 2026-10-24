# Factory: thin shell around the OpenHands agent (ADR 0005)

The process lives in the target repo (`AGENTS.md` + `.agents/skills`). This shell only adds what the agent cannot do
reliably: an isolated place to run, durable waits for a human, checks it cannot skip, and the PR.

```
ticket ─▶ app.py (127.0.0.1:8766) ─▶ shell.start: clone repo on host, branch ai/<id>
            worker thread ─▶ agent turn in Docker (OpenHands DockerWorkspace, runs/<id> mounted at /workspace)
              agent follows AGENTS.md: brief -> plan -> build -> QA, loops back on a QA GAP
              reply contains a question? ─▶ run parks "awaiting_decision" (container stops, conversation kept)
human answers (RunView Answer / POST /api/runs/<id>/answer) ─▶ same conversation resumes in a new container
              agent finishes ─▶ host checks: tests, protected files, QA VERDICT PASS
                 fail ─▶ failures sent back to the same conversation (max 2) ; pass ─▶ commit, push, PR (host gh)
human merges/closes the PR ─▶ dashboard marks the run merged/closed
```

| File | Job |
|---|---|
| `shell.py` | run record, repo setup, agent turn in Docker, question park/resume, checks, PR |
| `app.py` | RunView (`../dashboard/index.html`) + `POST /api/briefs`, `POST /api/runs/<id>/answer`, `GET /api/runs` |

## Run
```bash
uv venv .venv --python 3.12 && uv pip install --python .venv/bin/python -r requirements.txt
caffeinate -dimsu .venv/bin/python app.py      # http://127.0.0.1:8766 ; needs Docker, Ollama, your git + gh login
curl -X POST localhost:8766/api/briefs -H 'Content-Type: application/json' \
  -d '{"title":"average() returns the wrong value","brief":"..."}'   # or "+ New run" in the dashboard
```
Defaults (`app.py: DEFAULT_CFG`): trial repo `jagberg/ai-agent-trial-sandbox`, seeded on a throwaway base branch with
`bakeoff/fixture-qa`. Model `LLM_MODEL=ollama_chat/qwen3.8-27b-32k`, reached from the container at
`host.docker.internal:11434`. Agent image `ghcr.io/openhands/agent-server:1.21.0-python`, arm64; keep it on the same version as `openhands-sdk` (a 1.36 server writes event fields the 1.21 client rejects on resume).
On this Mac the worker waits while `~/llm-compare/STATUS.txt` is not `STATE: READY`.

## Verified (2026-10-23, run `run-20261023-213418`)
Agent asked the product owner -> run parked -> answered via the API -> resumed in a fresh container -> QA reported a GAP
(QA-only rounding rule) -> brief revised, rebuilt -> QA PASS -> host checks passed -> PR
https://github.com/jagberg/ai-agent-trial-sandbox/pull/5. Hidden tests 4/4 on the agent's code. 2 turns, 44 LLM calls,
~482k input tokens, ~15 min on qwen3.8:27b.

## Real ignite skills + Telegram (2026-10-24, run `run-20261024-151022`)
`DEFAULT_CFG` now seeds `bakeoff/fixture-ignite` (AGENTS.md adapter, `knowledge/calc.md`, OpenSpec propose/apply
skills) and copies the ignite plugin's `brief`, `plan`, `build` skills into each run, excluded from git (they are
CompareClub copyright; never commit them here). Brief approval is set by the shell when a human answers "approve...".
Result: PR https://github.com/jagberg/ai-agent-trial-sandbox/pull/6, hidden tests 5/5. Details: `CHANGELOG.md`.

Telegram relay (`telegram.py`, optional): create `~/.config/factory/telegram.env` (mode 600) with
`TELEGRAM_BOT_TOKEN=` (a dedicated bot) and `TELEGRAM_CHAT_ID=` (`.venv/bin/python telegram.py chat-id` after messaging
the bot). Questions arrive with the agent's reasoning; reply to answer. Check: `.venv/bin/python test_telegram.py`.

## Gotchas found
- **Conversation lease:** the agent server leases a conversation for 45 s and a stopped container does not release it;
  a resume inside that window fails with `ConversationLeaseHeldError` (HTTP 500). The shell closes the conversation and
  waits out the remainder before resuming. Only matters when an answer comes back within seconds.
- The agent server writes `conversations/` and `bash_events/` into its working dir, so the run folder (not the repo) is
  mounted at `/workspace` and the repo lives in `/workspace/repo`.
- `DockerWorkspace` defaults to `linux/amd64`; set `linux/arm64` on Apple silicon.

## Not built yet
Per-stage token/time split (the stage table shows the run's totals on the last stage), AI review comment on the PR,
Jira intake and an enterprise chat channel (Telegram is the trial relay), dashboard auth, Bedrock, running the shell itself in a container.
