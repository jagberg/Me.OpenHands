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
