# ADR 0005: Define the process in prompts inside an agent harness, not as coded workflow stages

- Status: accepted (2026-10-21) with the **OpenHands SDK** as the harness - see [Acceptance](#acceptance-2026-10-21)
- Date: 2026-10-19 (proposed), 2026-10-21 (accepted)
- Supersedes in part: ADR 0001 (stage order coded in a Temporal workflow)

## Context

The prototype (ADR 0001) codes the stage order in `blueprint/workflow.py`: brief -> decision gate -> plan -> build ->
reviews -> PR. On 2026-10-19 the owner rejected that shape for the long term: real work is not linear. An agent builds,
the QA skill finds a missing requirement, the team goes back to planning with an engineer or product manager who gives
new instructions, the agent rebuilds and QA reruns. In the owner's words, coding that loop is "essentially rebuilding
Claude Code but not as well as they have". The blueprint also cannot go back today: QA can only write CONCERNS, and the
run continues to a PR regardless.

Owner constraints still apply: no custom harness to maintain, open source and Docker preferred, no spend and no Claude
key until the setup is better defined (stated 2026-10-19).

## Decision (proposed)

Use an existing agent harness (an agent SDK) as the engine and define the AI-DLC in the target repo's prompts:
`AGENTS.md` for the process, `.agents/skills/*/SKILL.md` (the open Agent Skills format) for each stage, and sub-agents
where the harness supports them. The agent decides when to go back to the brief or plan.

Keep outside the agent only what an agent cannot do reliably:
- durable waiting for a human answer (minutes to days) and resuming the same session with it;
- hard checks the model cannot skip (tests, protected files, decisions pinned by tests - ADR 0002's principle, enforced
  by the harness's hooks or by the shell around it);
- metrics collection (prefer the harness's own telemetry over custom code).

Harness candidates, researched 2026-10-19 from vendor docs and repos:

| Harness | Licence | Models | Ask a human and resume | Status |
|---|---|---|---|---|
| OpenHands SDK | MIT | any via litellm | no built-in ask tool found; conversation persists and resumes | bake-off run |
| Codex SDK (`openai/codex`) | Apache-2.0 | built-in Ollama/LM Studio (`--oss`) and Amazon Bedrock, custom providers on the Responses API | threads resume by id; ask tool not confirmed | bake-off run |
| Claude Agent SDK | Anthropic Commercial Terms | Claude only (API, Bedrock); non-Claude via gateways unsupported | `AskUserQuestion` + defer/resume documented; per-skill OpenTelemetry | deferred: owner won't use a Claude key yet |
| Pi, OpenCode, Goose | MIT / unstated / unverified | multi-provider | not documented in what was read | not tested |

## Evidence so far

`bakeoff/README.md` (2026-10-19): OpenHands and Codex both run locally on qwen3:14b with repo skills and ~30 lines of
glue, but neither followed the prompt-defined process, looped back from QA, or asked the human. The model is the
bottleneck, so the bake-off has not yet ranked the harnesses.

## Alternatives considered

- **Keep the coded Temporal blueprint (ADR 0001)** - deterministic and auditable, but cannot model the build -> QA ->
  re-plan loop without growing into a custom harness.
- **Add a QA -> brief rewind to the blueprint** (QA returns a route, code enforces a loop budget) - small, but still owns
  the orchestration the owner wants to avoid.
- **Vendor platforms (Devin, Factory)** - no spend allowed yet; custom stage loops unconfirmed (`trials/`).
- **Workflow tools (n8n, Windmill)** - rejected 2026-10-18 as ETL-like.

## Consequences (if accepted)

- `blueprint/` stops being the orchestrator; Temporal stays only if durable cross-system waits need it.
- RunView (ADR 0004) would read the harness's session state and telemetry instead of Temporal queries.
- Reliability of the process depends on model quality; qwen3:14b is not enough. A stronger model is required before this
  can be judged, either a larger free local model or Bedrock (spend).
- To accept: pick a harness after a bake-off on a stronger model shows it (1) follows the process, (2) loops back on a
  QA gap, (3) asks a human and resumes with the answer.

## Acceptance (2026-10-21)

**Harness: OpenHands SDK** (owner's choice, 2026-10-21).

Evidence (`bakeoff/README.md`, rounds 2-3, local `qwen3.8:27b` at 32k context, $0): OpenHands and Codex both passed
3 of 3 trials - followed the prompt-defined process, caught the spec requirement, asked the product owner, resumed the
same session with the answer, QA PASS, all hidden tests green. The model chosen by the separate local-LLM benchmark
(qwen3.8:27b) was enough where qwen3:14b was not.

Why OpenHands over Codex when behaviour tied:
- **Bedrock model freedom.** Codex's built-in `amazon-bedrock` provider officially supports only OpenAI GPT models
  (OpenAI help article "Configure Codex with Amazon Bedrock", checked 2026-10-21). OpenHands reaches any model through
  litellm, including Claude on Bedrock - untested here.
- Pure Python and already used by `blueprint/` and RunView; Codex adds the Codex CLI binary to the stack.

Accepted costs and open items:
- **No built-in command sandbox** when OpenHands runs on the host (Codex has one). OpenHands must run inside Docker.
- Two OpenHands quirks to guard against: with project skills loaded and `reasoning_effort="none"`, qwen3 returned empty
  replies on every turn (leave reasoning on); a skill with invalid YAML frontmatter is skipped with only a log warning
  (validate skills before use).
- No built-in "ask a human" tool: the agent ends its turn with a question and the shell resumes the conversation with
  the answer. The prompt-format convention needs a tolerant parser (`find_question()` in `bakeoff/harness/`).
- **QA -> brief loop-back is still unproven**: in every trial the brief caught the requirement first.
- Codex remains the alternative if GPT models on Bedrock become acceptable and a built-in sandbox matters more.

Consequences now in force: `blueprint/` stops being the orchestrator of stage order. Temporal's remaining role (durable
waits, if any) and RunView's data source move to the design of the thin shell around OpenHands.

**Update 2026-10-22:** QA -> brief loop-back proven on OpenHands (`bakeoff/README.md`, round 4): with a requirement only
QA could see, QA reported a GAP, the agent revised the brief, re-planned, rebuilt and QA passed (4/4 hidden tests), with
the loop driven only by `AGENTS.md` and the skills. Single run; the "still unproven" item above is resolved.
