# ADR 0001: Orchestrate coding agents with Temporal + the OpenHands SDK

- Status: accepted (local prototype, 2026-10-18); revisit before the work-repo rollout.
  Under review since 2026-10-19: [ADR 0005](0005-process-in-prompts-agent-harness.md) (proposed) would move stage order
  out of code and into prompts inside an agent harness.
- Date: 2026-10-18

## Context

Goal (from the owner, 2026-10-18): an "AI software factory" for the team's AI-DLC. A brief arrives from Jira or chat,
agents run the ignite skills (`ignite:brief`, `ignite:plan`, `ignite:build`) plus engineering, security and QA skills,
can ask a named human a decision, raise a PR, get an AI review, and a human does the final review and merge. A
dashboard must show the current state and metrics along the whole lifecycle. The model should eventually be AWS Bedrock.

Constraints stated by the owner:
- No spend until the shape of the factory is clear (vendor trials ruled out, 2026-10-18).
- Open source, runnable in Docker locally first, expandable later.
- Nobody is dedicated to maintaining it, so upkeep must stay small.
- The human-in-the-loop and lifecycle metrics are the key requirements.

## Decision

Build the factory as a **Temporal workflow ("blueprint")** whose steps are either plain code (setup, tests,
validation, PR) or **OpenHands agent runs driven through the OpenHands Python SDK**. Temporal runs in Docker
(`blueprint/docker-compose.yml`); the worker is ~450 lines of Python in `blueprint/`.

The blueprint shape follows Stripe's "Minions" (fixed sequence of deterministic and agentic nodes, human review at the
PR) and Uber's Minion (stop at a draft-quality PR with a validation table). Uber's platform layers (model gateway,
MCP gateway, context graph, skills marketplace) were explicitly **not** copied: they assume a large platform team.

OpenHands is used via the **SDK, not the CLI or GUI**: the CLI loads ~100 user and public skills into the prompt
(including the owner's personal `~/.agents/skills`), which pushed a 14B local model off task in the first smoke test
(2026-10-18, it answered an unrelated "competitive intelligence" prompt). The SDK lets us pass
`AgentContext(load_user_skills=False, load_public_skills=False)` and read token/latency metrics per stage.

## Alternatives considered

Researched 2026-10-17/18 from vendor docs and third-party write-ups; none were run except where noted.
- **Devin / Factory (buy)** - cover most of the flow (Jira/Slack intake, PRs, review); cloud agents need paid plans
  (Devin Pro $20/mo, Factory Pro $20/mo per their pricing pages); Bedrock not confirmed for Devin; running our own
  ignite stages as gates unconfirmed. Trial pack prepared in `trials/` for later.
- **OpenHands Enterprise** - Jira DC/Slack integrations and automations, self-hosted in a VPC; custom pricing; no
  documented runs/metrics dashboard.
- **OpenHands open-source GUI** (`openhands serve`) - single user, conversation list only; its Automations page
  errored locally (2026-10-18).
- **Coder Agents** - self-hosted, Bedrock supported, plan-review step; enterprise offering; Jira/PR/dashboard not
  documented.
- **Multica** - issue board with agents as teammates, Docker; Jira/Bedrock unverified, licence unclear.
- **n8n / Windmill** - workflow automation with approval steps; rejected by the owner as "more like an ETL process".
- **AWS ABCA sample** - Jira/Slack to PR on AWS; experimental, maintenance mode, AWS CDK only, no human questions.
- **Custom engine (our own state machine)** - started and deleted (2026-10-18) because the owner preferred a
  third-party base over maintaining an orchestrator.

## Consequences

- Durable state, retries, timers and a stock UI come from Temporal; we maintain only the blueprint code and skills.
- We do maintain glue (~450 lines) and a small custom dashboard (see ADR 0004).
- Jira and Google Chat intake are **not built**; the dashboard API (`POST /api/briefs`, `POST /api/runs/<id>/answer`)
  is the intended integration point.
- Bedrock is a config change (`LLM_MODEL=bedrock/<model-id>`, `LLM_BASE_URL=`) but **untested**.
- The local model (`qwen3:14b`, 32k context) is the weakest link: thin plans, ignored instructions. See ADR 0002.
- The containerised worker image builds, but has **not** been run against Temporal (needs a repo-scoped `GH_TOKEN`).
