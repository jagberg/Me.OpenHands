# ADR 0002: Human decisions are a workflow step and are enforced by tests

- Status: accepted
- Date: 2026-10-18

## Context

The test ticket (`trials/TICKET.md`) tells the agent to ask a human how `average([])` should behave before
implementing it. Three runs on the Temporal blueprint (2026-10-18, repo `jagberg/ai-agent-trial-sandbox`) showed:

| Run | Mechanism | Result |
|---|---|---|
| `ignite-20261018-203927` | Agent asked to write `.ignite/QUESTION.md` when it needs a human | Never asked. PR #1 shipped without the decision. |
| `ignite-20261018-205004` | Structured decision gate asked; human answered "return 0" | Build ignored the answer; QA passed it. PR #2 wrong. |
| `ignite-20261018-210055` | Gate + "each decision must be pinned by a test" check | Implemented, `test_decisions.py` added, 3 tests pass. PR #3 merged. |

Instructions to the agent were not enough with a weak model; neither asking nor obeying the answer was reliable.

## Decision

1. **Decision gate**: after `ignite-brief`, one narrow LLM call (not an agent loop) returns the open decisions as
   JSON. Plain code turns each into a BLOCKING question and the workflow waits on a Temporal signal (`answer`).
2. **Decision tests**: the build must add one test per answered decision to `test_decisions.py`. Plain code counts
   them and runs the test command; the build is sent back (max 3 attempts) until both pass, otherwise the run fails
   and no PR opens.
3. Agents may still ask ad hoc via `.ignite/QUESTION.md` (`BLOCKING:` parks, `ASK:` continues on its assumption).

## Alternatives considered

- **Agent-only questions (QUESTION.md)** - unreliable with a 14B model (run 1).
- **Trust the build and QA agents to apply decisions** - run 2: both missed it.
- **Human checks decisions only at PR review** - catches it late, after the full pipeline has run.

## Consequences

- The human gate cannot be skipped by the model, and a decision cannot reach a PR unimplemented.
- Counting `def test_` is a coarse proxy: it proves tests exist and pass, not that they encode the decision correctly.
  The human PR review is still the final check.
- A stronger model (Bedrock Claude) may make agent-initiated questions reliable; keep the deterministic gate anyway.
