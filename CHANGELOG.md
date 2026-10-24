# Changelog

Dated, append-only. Architecture decisions are in `docs/adr/`.

## 2026-10-17 - OpenHands installed for local evaluation

**Decision:** Install OpenHands CLI v1.16.0 with `uv tool install openhands --python 3.12` (per
https://docs.openhands.dev/openhands/usage/run-openhands/local-setup) and create a throwaway bug repo at
`~/code/openhands-sandbox`.
**Reasoning:** Evaluate OpenHands before committing to an agent platform.
**Trade-off accepted:** `~/.local/bin` is not on PATH by default on this machine; left unchanged.
**Supersedes:** n/a

## 2026-10-18 - Local Ollama instead of a hosted model

**Decision:** Run agents on Ollama `qwen3:14b` via a derived model `qwen3-14b-oh` (32k context).
**Reasoning:** Zero spend and no API keys while the factory shape is unclear.
**Trade-off accepted:** Slow (about 1-2 min per stage) and unreliable at following instructions (see ADR 0002).
**Alternatives rejected:** Hosted Anthropic key: spend and key handling not wanted yet.
**Supersedes:** n/a

## 2026-10-18 - Script pipeline and first dashboard (`pipeline/`, `dashboard/`)

**Decision:** A Python script runs dummy ignite stages through the OpenHands SDK, opens a PR on `jagberg/Me.Compass`
against a throwaway base branch, and writes metrics to `runs/<id>/run.json` for a local dashboard.
**Reasoning:** Prove the agent can fix the test bug and that SDK metrics (tokens, latency, tool calls) can be captured.
**Trade-off accepted:** No durable state, no human questions. Kept for reference only.
**Supersedes:** n/a

## 2026-10-18 - Dashboard restyled after Checkr's ForgeView

**Decision:** Runs page with tiles (running, awaiting human, failed, completed), filters and a runs table.
**Reasoning:** The owner's reference for the initiative was a screenshot of ForgeView (Checkr AgentForge) and Luca
Bonmassar's post on AI-assisted / AI-first / AI-native maturity.
**Supersedes:** first dashboard layout.

## 2026-10-18 - Custom orchestrator abandoned

**Decision:** Stop building a custom state-machine engine.
**Reasoning:** Owner preference: use a third-party open-source base instead of maintaining an orchestrator.
**Supersedes:** n/a (the engine was never committed).

## 2026-10-18 - Vendor trial pack prepared, no trials run (`trials/`)

**Decision:** Prepare a ticket, scorecard, vendor request and runbook for Devin and Factory, and a private trial repo
`jagberg/ai-agent-trial-sandbox`; do not sign up.
**Reasoning:** Owner will not spend before the factory shape is clear; cloud agents on both start at $20/mo.
**Supersedes:** n/a

## 2026-10-18 - Temporal blueprint chosen for the prototype

**Decision:** See ADR 0001 (Temporal + OpenHands SDK) and ADR 0002 (deterministic human gates and decision tests).
**Supersedes:** script pipeline as the main path.

## 2026-10-18 - Blueprint v2

**Decision:** See ADR 0003. History per run dropped from 445 to 99 events; issue/resolution summary added to Temporal
UI, RunView and the PR body.
**Supersedes:** blueprint v1 (`blueprint/workflow_v1.py`, frozen until its runs finish).

## 2026-10-18 - Two dashboards

**Decision:** See ADR 0004. Comparison page and screenshots in `docs/visuals/`.
**Supersedes:** n/a

## 2026-10-19 - Repository made public

**Decision:** The owner made `jagberg/Me.OpenHands` public.
**Reasoning:** Not recorded (owner's choice). A history audit the same day found no secrets, local paths, hostnames or
work email; known exposures are the personal commit email (already public via other repos), links to the private
`ai-agent-trial-sandbox` repo and private artifact pages, and no LICENSE file (all rights reserved by default).
**Trade-off accepted:** Anyone can read the history, including old `runs/*.json` metric files from the first commit.
**Supersedes:** n/a

## 2026-10-19 - Setup visual with conceptual and logical views

**Decision:** Add `docs/visuals/setup-steps.html`: six-layer conceptual view, per-component configuration (logical
view), interfaces between components, and eight setup steps including the three ways to send a human answer.
**Supersedes:** n/a

## 2026-10-19 - Coded stage order under review

**Decision:** Propose moving the AI-DLC from coded workflow stages into prompts inside an agent harness (ADR 0005,
proposed); ADR 0001 is marked under review, unchanged otherwise.
**Reasoning:** Work loops (QA finds a gap, a human re-plans, rebuild). The owner does not want to rebuild an agent
harness in workflow code. The blueprint also cannot go back from QA today.
**Trade-off accepted:** Process reliability moves onto the model; qwen3:14b is not good enough to judge it.
**Alternatives rejected:** Add a QA -> brief rewind to the blueprint: still owns orchestration.
**Supersedes:** n/a yet (ADR 0005 is proposed)

## 2026-10-19 - Harness bake-off: OpenHands SDK vs Codex SDK

**Decision:** Run both on the same prompt-defined process, fixture and local model before choosing; Claude Agent SDK
deferred until the owner is ready to use a Claude key.
**Reasoning:** Codex is open source (Apache-2.0) with built-in Ollama and Bedrock providers; OpenHands is MIT and already
proven here. Both can be tested at $0.
**Result:** Wiring works on both (~30 lines of glue, repo skills load, token metrics); neither followed the process,
looped back from QA or asked the human on qwen3:14b, so the harnesses are not ranked yet. Full table in `README.md`,
details in `bakeoff/README.md`.
**Trade-off accepted:** Single run per harness on a weak model; conclusions are about wiring, not quality.
**Supersedes:** n/a

## 2026-10-21 - OpenHands chosen as the agent harness; ADR 0005 accepted

**Decision:** Build the factory on the OpenHands SDK with the process in prompts; local model `qwen3.8:27b` (32k).
**Reasoning:** On qwen3.8:27b (picked by a separate local-LLM benchmark) OpenHands and Codex both passed 3/3 trials
(asked the human, resumed, QA PASS, hidden tests green). Codex's Bedrock provider is limited to OpenAI GPT models;
OpenHands keeps any Bedrock model, including Claude, open.
**Trade-off accepted:** No built-in command sandbox (must run in Docker); question detection relies on a prompt
convention with a tolerant parser; QA -> brief loop-back not yet proven.
**Alternatives rejected:** Codex SDK: Bedrock limited to GPT models, extra CLI binary. Claude Agent SDK: deferred, owner
not using a Claude key yet.
**Supersedes:** ADR 0001 in part (stage order in code); ADR 0005 status proposed -> accepted.

## 2026-10-22 - QA loop-back proven on OpenHands

**Decision:** None new; evidence for ADR 0005. Round 4 of the bake-off (`bakeoff/fixture-qa`) hid a requirement in a
QA-only checklist; OpenHands on qwen3.8:27b asked the product owner, then QA reported the gap, the agent revised the
brief, re-planned, rebuilt and passed QA and 4/4 hidden tests.
**Trade-off accepted:** Single run; 11.5 min and 379k input tokens for a one-line fix on the local model.
**Supersedes:** n/a (resolves the "loop-back unproven" item in ADR 0005)

## 2026-10-23 - Factory shell around OpenHands built and verified

**Decision:** Implement ADR 0005 as `factory/`: the agent runs in an OpenHands `DockerWorkspace` (commands never run
on the host); a question parks the run and the answer resumes the same conversation in a new container; host-side
checks (tests, protected files, QA verdict) gate the PR; git/gh stay on the host so credentials never enter the container.
**Reasoning:** Keep only what the agent cannot do reliably outside it; reuse OpenHands' own isolation and conversation
persistence instead of building them.
**Trade-off accepted:** A 45 s conversation lease means a resume waits out the remainder if an answer arrives within
seconds; one agent at a time (one local model); per-stage metrics not split yet.
**Result:** Run `run-20261023-213418`: asked, parked, resumed, QA loop-back, checks passed, PR #5 on the trial repo,
hidden tests 4/4.
**Supersedes:** `blueprint/` as the main path (kept as the earlier prototype).

## 2026-10-24 - Flint 40B tried; qwen3.8:27b stays the local model

**Decision:** Keep `qwen3.8:27b` (32k) as the factory's local model. Recursive's Flint (`flint:40b`, 39.8B MoE with
about 2.5B active, released 2026-10-21) is a speed candidate only.
**Reasoning:** Bake-off round 5 (`bakeoff/README.md`) ran Flint on the round 4 test. It asked the product owner and
passed 4/4 hidden tests in 194 s, but its brief step read `qa/checklist.md`, which `AGENTS.md` reserves for qa-review,
so the QA loop-back never happened. Following the prompt-defined process is the point of ADR 0005, so a fast model that
skips a rule loses. A control rerun of qwen3.8 on the upgraded Ollama passed the full loop-back in 426 s (690 s before).
**Trade-off accepted:** Flint is about 2.2 times faster than qwen3.8 on the same Ollama. Its memory use (22 GB, swap
+10.3 GB in `~/llm-compare/RESULTS.md`) is also too high to run beside other apps on a 32 GB Mac. Single runs only.
**Environment change:** Ollama on the development Mac was upgraded from 0.33.1 to 0.40.9 by the separate benchmark
(Flint needs 0.40.8 or newer). qwen3.8 still runs on the `llamacpp` runner; Flint ran on MLX. The factory itself
(`factory/`) has not been re-run on 0.40.9.
**Revisit when:** a stricter `qa/` rule in `AGENTS.md` plus repeat runs show Flint follows the process, or the factory
moves to hardware with spare memory.
**Supersedes:** n/a

## 2026-10-24 - HumanLayer open-sourced: watched, not adopted

**Decision:** Do not replace `factory/` with HumanLayer (`github.com/humanlayer/humanlayer`, Apache-2.0, open-sourced
in "Open Sourcing HumanLayer", Dexter Horthy, LinkedIn, Oct 2026) yet.
**Reasoning:** It covers the parts of the factory that are custom here (dashboard, team view, human steering, Jira and
Slack integrations; tasks, sessions, plans, diffs and PRs in its data model) and matches the owner's preference for a
third-party base. But as of 2026-10-24: self-hosted processes refuse to start without third-party keys (WorkOS, Slack,
Linear, ...), which conflicts with the no-keys, no-spend constraint; the stack is about 8 services (Postgres, Electric,
MinIO, Redis, durable-streams, API, apps, a daemon per host), against two Python files; the daemon drives Claude Code
and Codex, not OpenHands (OpenCode support is open issue #1119); and there is no stated maintenance commitment
(open bug #1126: daemon leaks a Claude process per idle session).
**Revisit when:** the keys become optional. Then spike HumanLayer + Codex + local Ollama on the trial repo; pass if a
run is visible, a question reaches a human and returns, and the run ends in a PR. Adopting it would reopen ADR 0005,
because the harness would become Codex, whose Bedrock provider officially supports GPT models only.
**Supersedes:** n/a

## 2026-10-24 - Real ignite skills and a Telegram relay in the factory

**Decision:** The factory runs the CompareClub ignite plugin's own `brief`, `plan` and `build` skills (v0.4.0, unmodified)
with OpenSpec 1.15 as the spec engine, and relays questions through a Telegram bot.
**Reasoning:** The stand-in skills proved the loop; the real skills are what a work-repo pilot will run. OpenSpec's
`openspec init --tools agents` writes `.agents/skills`, which OpenHands loads natively, so `opsx:propose` and
`opsx:apply` map to existing skills instead of new glue. Telegram was chosen as a local, free, two-way channel
(long polling, no public URL) until an enterprise channel (Google Chat, possibly via CC.Tool.Alfred) is set up.
**How:**
- The ignite skills are copyright CompareClub, all rights reserved, so the shell copies them into each run's workspace
  from the installed plugin and lists them in `.git/info/exclude`. They are never committed, pushed or published (this
  repo is public).
- OpenHands requires a skill's `name` to match its directory, so the skills live at `.agents/skills/{brief,plan,build}`.
- `bakeoff/fixture-ignite/` holds a repo-specific `AGENTS.md` adapter (the skills' "ask the user" = the QUESTION line;
  PRD destination and engine come from `knowledge/calc.md`) and the two OpenSpec skills the plan and build steps use.
- Brief approval stays a human gate in code (ADR 0002): an answer starting with "approve" makes the shell set
  `Status: approved`; the agent never writes it, and a pre-PR check fails on any unapproved brief.
- The ignite + OpenSpec skills are about 60 KB, so the agent uses OpenHands' `LLMSummarizingCondenser` to fit 32k.
- `factory/telegram.py` (stdlib only): questions (with the agent's reasoning) go to one configured chat; a reply answers
  the question it replies to; other chats, bot commands and messages sent while the relay was down are ignored.
  Token and chat id live in `~/.config/factory/telegram.env` (mode 600), outside the repo.
**Result:** Run `run-20261024-151022`, ticket "Add median() to calc": brief drafted, changes requested, revised,
approved (code flipped the status); OpenSpec proposal (`openspec validate` passes); design-review gate; apply,
tests, QA PASS; all host checks including `brief_approved`; PR https://github.com/jagberg/ai-agent-trial-sandbox/pull/6.
Hidden tests (`bakeoff/hidden/test_hidden_median.py`) 5/5. No ignite skill files in the PR. 7 agent turns, 2,437 s of
agent time, 88 LLM calls, 1.15M input tokens, 5 human questions (the last two answered from Telegram).
**Found and fixed on the way:** (1) a question stated in an earlier message of a turn ("see QUESTION line above") was
missed; the parser now also matches "stopping to ask". (2) The relay took the bot's `/start` setup message as the answer
to the design-review gate; `ignite:build` refused it as not an explicit yes and asked again, so the prompt-level gate
held, and the relay now ignores commands and backlog. (3) Telegram showed only the question line; it now includes
the agent's reasoning.
**Trade-off accepted:** Slow and token-heavy on the local model (about 40 minutes of agent time for a small function).
Telegram is a personal app, for this trial only. The design-review gate is enforced by the skill's prompt, not by code;
it held once against a non-answer, which is evidence, not proof.
**Supersedes:** the stand-in ignite skills as the factory default (`fixture-qa` kept as `QA_CFG` in `factory/app.py`).

## 2026-10-25 - Resume really resumes; per-stage metrics in RunView

**Decision:** Keep one OpenHands conversation per run across containers, pin the agent-server image to the SDK version,
nudge the agent when it stops on a plain message, and show per-stage metrics in RunView.
**Correction to the record:** The 2026-10-23 and 2026-10-24 entries above say an answer "resumes the same conversation".
It did not. `Conversation()` defaults to `delete_on_close=True`, so `conv.close()` deleted the conversation after every
turn, and each resume (PR #5, PR #6) started a fresh conversation that rebuilt context from the repo files. Found
2026-10-24 because `runs/<id>/conversations/` was empty. Those runs still passed, which shows the repo files carried
enough state, but they are not evidence that resume works.
**What changed (`factory/shell.py`):**
- `delete_on_close=False`. Resuming then failed with `ValidationError ... extended_content Extra inputs are not
  permitted`: the 1.36.0 server wrote event fields the 1.21.0 client rejects. The default image is now
  `ghcr.io/openhands/agent-server:1.21.0-python`; keep it on the same version as `openhands-sdk`.
- In the SDK a text-only reply ends the run ("awaits user input", `agent/response_dispatch.py`). With the conversation
  kept, qwen3.8 did this mid-process ("Let me view the full file to verify.") and burned both check retries. The shell
  now sends a "continue" nudge in the same container (max 6 per turn) unless the agent called `finish` or asked a
  QUESTION. Check retries are left for real check failures.
- The OpenSpec CLI is installed under `/workspace/.tools` (`bakeoff/fixture-ignite/AGENTS.md`): each resume is a new
  container and a global npm install was lost every turn.
- `POST /api/runs/<id>/retry` re-queues a failed run in its conversation; a retry waits out the 45 s lease after a
  failed turn too.
- RunView shows per stage: agent time, LLM calls, tool calls, tokens and human wait, split from the conversation events
  at each `.ignite/log.md` line (`stage_metrics`, self-check `factory/test_metrics.py`).
**Result:** Run `run-20261025-081007`, "Add median() to calc": one conversation for all 7 turns, 3 human questions
(empty-list rule, brief approval, design review), 2 nudges, all host checks, PR
https://github.com/jagberg/ai-agent-trial-sandbox/pull/7, hidden tests 5/5, no ignite skill files in the PR. 1,953 s of
agent time, 67 LLM calls, about 1.03M input tokens. Plan was the heaviest stage (1,228 s, 606k input tokens).
**Trade-off accepted:** A kept conversation grows, so later turns send more tokens (summarised by the condenser) than
the fresh-conversation runs did. The nudge is a workaround for a local-model habit; a model that calls `finish` never
sees it. `caffeinate -s` does not stop sleep on battery: one run failed when the Mac slept (container start timed out).
**Supersedes:** the "same conversation resumes" claims in the 2026-10-23 and 2026-10-24 entries (kept as written).
