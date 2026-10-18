# ADR 0004: Stock Temporal UI for operators, small custom RunView for humans in the loop

- Status: accepted
- Date: 2026-10-18

## Context

The owner wants one place that shows the current state of each agent run, metrics along the lifecycle, and a way to
inject a human decision. The visual reference was a "ForgeView" runs page for Checkr's AgentForge (status tiles:
running / awaiting human / failed / completed; runs table with workflow, agent, environment, trigger, duration, pending).

Two UIs exist after the prototype:
- **Temporal Web UI** (stock, `:8233`): state, full history, Timeline, retries/reset/cancel, and with v2 a live
  "issue and resolution" summary in the User Metadata tab. It can send signals and start workflows, but only as raw JSON.
  It cannot chart tokens, cost or per-stage timing without forking it.
- **RunView** (`dashboard/`, custom, `:8765`): ForgeView-style tiles and runs table, per-stage tokens/time/LLM calls,
  Issue and Resolution side by side, Answer buttons that send the Temporal signal, a New run button.

## Decision

Keep both: **Temporal UI for whoever operates the system** (debugging, retries, history), **RunView for whoever
answers questions and reads metrics**. RunView stays small (one HTML file, one stdlib HTTP server) and reads all v2
state from Temporal, so it stores nothing of its own.

## Alternatives considered

- **Temporal UI only** - possible with search attributes as columns plus the summary panel; loses metrics charts and
  friendly answer buttons (non-engineers would type JSON).
- **OpenHands GUI** - conversation list only; no lifecycle or cross-run metrics.
- **Langfuse** (open-source LLM observability) - good token/cost traces per LLM call, but no lifecycle stages or human
  gates, and a heavier stack (Postgres, ClickHouse, Redis, MinIO). Add later only if cost analytics matter.

## Consequences

- We maintain ~240 lines of dashboard code.
- RunView has **no authentication** and binds to 127.0.0.1. It must get auth before it is exposed on any network.
- Screenshots and the v1/v2 comparison page are in `docs/visuals/`.
