# Me.OpenHands - agentic SDLC prototype

A local prototype of an "AI software factory": a ticket goes through the ignite stages, engineering/security/QA
reviews and a PR, with humans answering decisions and doing the final review. Built on **Temporal** (workflow, state,
retries, UI) and the **OpenHands SDK** (coding agents), running on a local Ollama model.

Decisions: `docs/adr/` and `CHANGELOG.md` - read before proposing architecture changes.
Setting this up on a work repo: `docs/work-repo-setup.md`.

> **Direction (accepted 2026-10-21):** [ADR 0005](docs/adr/0005-process-in-prompts-agent-harness.md) replaces the coded
> stage order below with a process defined in prompts (`AGENTS.md` + skills) inside the **OpenHands SDK**, because real
> work loops (build -> QA finds a gap -> re-plan with a human -> rebuild) and coding that loop means rebuilding an agent
> harness. Local model: `qwen3.8:27b` (32k context). The Temporal blueprint below is the earlier prototype.

## Current state (2026-10-18)

```
ticket -> setup* -> ignite-brief -> decision gate* -> [HUMAN answers] -> ignite-plan -> ignite-build
       -> tests* + decision tests* (back to build, max 3) -> engineering / security / QA reviews
       -> validate* -> open PR* -> AI review -> [HUMAN merges or closes] -> done          (* = plain code)
```

| Folder | What | Status |
|---|---|---|
| `blueprint/` | Temporal workflow (v2), activities, worker, skills, Docker compose | main path |
| `dashboard/` | RunView: runs, metrics, Answer buttons, New run (reads Temporal) | in use |
| `docs/adr/` | Why it is built this way | 4 ADRs |
| `docs/visuals/` | v1 vs v2 comparison page, dashboard screenshots | reference |
| `factory/` | Thin shell around the OpenHands agent: Docker isolation, ask -> park -> resume, pre-PR checks, PR, RunView on :8766 | main path, verified 2026-10-23 |
| `bakeoff/` | OpenHands SDK vs Codex SDK on the same prompt-defined process (harnesses, fixture, results) | run 2026-10-19 |
| `trials/` | Devin/Factory trial pack (ticket, scorecard, vendor request) | not run |
| `pipeline/` | First script-based pipeline | superseded, kept for reference |

Run it: see `blueprint/README.md`. UIs: Temporal http://localhost:8233, RunView http://localhost:8765.

Known limits of the current blueprint: local `qwen3:14b` is weak (thin plans, ignores instructions), Jira/Chat intake not built, RunView has no
auth, Bedrock path untested, containerised worker not run end to end.

## Harness bake-off (2026-10-19)

Same fixture, ticket, scripted product-owner answer and local model (Ollama qwen3:14b, 32k context) on both; no API
keys, $0. The process lives only in `AGENTS.md` and `.agents/skills/*/SKILL.md`. The ticket omits a spec requirement
(ignore `None`) that QA should catch, and a product decision (empty list) the agent should ask a human about; hidden
tests score both. Details and raw results: [`bakeoff/README.md`](bakeoff/README.md).

| | **OpenHands SDK** | **Codex SDK** |
|---|---|---|
| Harness code needed | 33 lines | 25 lines |
| Loaded the repo's skills and `AGENTS.md` | Yes, but it silently skipped a skill with invalid YAML (a fixture bug, now fixed) | Yes |
| Followed the process (brief → plan → build → QA) | **No**: ignored `AGENTS.md` and went straight to the fix | **Faked it**: wrote all four log lines in one command up front, never ran QA |
| Fixed the basic bug | **Yes**: visible tests pass, `test_basic` passes | **No**: never used its edit tool; 15 failed `sed -i` attempts (macOS syntax), then gave up |
| QA caught the missing `None` requirement and looped back | No | No |
| Asked the human about empty lists | No | No |
| Metrics with no extra code | LLM calls (17), tokens in/out (121k / 9.5k) | Tokens in/out (270k / 8.4k), per-turn usage, context window |
| Wall time | 9.5 min | 8.3 min |
| Local-model gotchas | Reasoning off + skills loaded → empty replies on every turn (fixed by leaving reasoning on) | Needs the `:latest` tag or it tries to download the model; `exec` defaults to read-only; assumed a 258k context window (corrected to 32k) |

**Findings**
1. Wiring works on both at $0: local Ollama model, repo skills from `.agents/skills` + `AGENTS.md`, token metrics,
   about 25-35 lines of glue.
2. The model is the bottleneck, not the harness: qwen3:14b cannot hold a multi-step prompt-defined process on either,
   matching blueprint runs 1-2 (ADR 0002). The bake-off therefore cannot yet rank the harnesses on the natural
   build -> QA -> re-plan loop.
3. The ask-a-human path is unproven on both: neither model chose to ask.
4. Licences and models (from repos/docs, 2026-10-19): OpenHands MIT, any model; Codex Apache-2.0, built-in Ollama /
   LM Studio and Amazon Bedrock providers; Claude Agent SDK is Claude-only under Anthropic's Commercial Terms and is
   deferred until the owner is ready to use a Claude key.

### Rounds 2-3 on qwen3.8:27b (2026-10-21)

Same fixture; 32k context; the ticket now requires asking the product owner. Round 3 used the same tolerant question
relay for both harnesses (round 2's strict relay missed OpenHands' differently worded question).

| Round 3 (3 trials each) | **OpenHands SDK** | **Codex SDK** |
|---|---|---|
| Asked, resumed, finished | 3/3 | 3/3 |
| Hidden tests | 3/3 in every trial | 3/3 in every trial |
| QA verdict | PASS in every trial | PASS in every trial |
| Time / tokens in | 6-12 min / 157-254k | 6-12 min / 121-271k |
| Bedrock later | any model via litellm, incl. Claude (untested) | OpenAI GPT models only |
| Sandbox for agent commands | none on the host (run in Docker) | built in |

**Decision: OpenHands** (ADR 0005 accepted): tied on behaviour, and it keeps the Bedrock model choice open.
QA loop-back proven on 2026-10-22 (round 4): with a requirement only QA could see, QA reported a GAP, the agent revised
the brief, rebuilt and passed 4/4 hidden tests, driven only by `AGENTS.md` and the skills. Details:
[`bakeoff/README.md`](bakeoff/README.md).

## Evolution of thinking

1. **2026-10-17** - OpenHands GUI (`openhands serve`) installed per the official docs. Single-user conversation UI, no
   runs dashboard, Automations page errored locally.
2. **2026-10-18** - Script pipeline (`pipeline/`) on Ollama via the OpenHands SDK, PR on `jagberg/Me.Compass`. The CLI
   was dropped because it loads ~100 user/public skills into the prompt and the 14B model went off task.
3. **2026-10-18** - Dashboard restyled after Checkr's ForgeView. Custom orchestrator started, then abandoned in favour
   of a third-party base.
4. **2026-10-18** - Platforms surveyed (OpenHands Enterprise, Coder Agents, Multica, n8n, Windmill, AWS ABCA, Devin,
   Factory). No spend allowed, so Devin/Factory trials were prepared but not run.
5. **2026-10-18** - Temporal blueprint (ADR 0001). Human gates became deterministic after the model skipped and then
   ignored decisions (ADR 0002). v2 cut history from 445 to 99 events and added issue/resolution summaries (ADR 0003).
6. **2026-10-19** - Repo made public. Owner rejected coded stage order for the long term: the natural loop
   (QA finds a gap, a human re-plans, rebuild) belongs in an agent harness, not hand-built workflow code (ADR 0005,
   proposed). Agent SDKs surveyed (Claude Agent SDK, OpenHands, Codex, Pi, OpenCode, Goose); OpenHands and Codex
   bake-off run on the local model (above).
7. **2026-10-21** - A separate local-LLM benchmark picked `qwen3.8:27b`. On it both harnesses passed 3/3; OpenHands
   chosen for Bedrock model freedom (ADR 0005 accepted, ADR 0001 superseded in part).
8. **2026-10-23** - `factory/` built: OpenHands agent in Docker, question -> park -> resume in a fresh container,
   host-side checks and PR. First end-to-end run produced PR #5 on the trial repo with the QA loop-back.
9. **2026-10-24** - Flint 40B tried on the loop-back test: 4/4 and about 2.2 times faster than qwen3.8, but it read the
   QA-only checklist early, so the loop-back never ran; qwen3.8 stays. HumanLayer open-sourced; watched until its
   self-hosted stack runs without third-party keys (`CHANGELOG.md`).
10. **2026-10-24** - The factory runs the real ignite skills (unmodified, never committed) with OpenSpec, and relays
   questions through Telegram. First run: brief revised and approved, design review, build, QA, PR #6 on the trial
   repo, hidden tests 5/5.
