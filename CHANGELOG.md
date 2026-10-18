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
