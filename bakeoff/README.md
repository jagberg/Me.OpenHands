# Harness bake-off: OpenHands SDK vs Codex SDK (2026-10-19)

Same fixture, same ticket, same scripted human answer, same local model (Ollama `qwen3-14b-oh`, qwen3:14b with 32k
context). No Claude or OpenAI key, $0. The process is defined only in prompts (`fixture/AGENTS.md` and
`fixture/.agents/skills/*/SKILL.md`); each harness only starts the agent and relays a `QUESTION:` line to a scripted
product owner. Rationale and outcome: ADR 0005 (accepted 2026-10-21 with OpenHands). Round 1 (qwen3:14b) is below;
rounds 2-3 (qwen3.8:27b) are in [Rounds 2-3](#rounds-2-3-qwen3827b-2026-10-21).

## What the fixture tests
- `calc.py` has the off-by-one bug from the original sandbox.
- `docs/spec.md` adds a requirement the ticket omits (ignore `None`) - QA should catch the gap and loop back to the brief.
- `docs/spec.md` reserves empty-list behaviour for the product owner - the agent should ask; the scripted answer is
  "return 0 for an empty list (and for a list of only None values); do not raise."
- `hidden/test_hidden.py` scores the result; the agents never see it.

## Results

| | OpenHands SDK 1.21.0 | Codex SDK / CLI 0.163.0 |
|---|---|---|
| Harness glue | 33 lines (`harness/oh_harness.py`) | 25 lines (`harness/codex_harness.py`) |
| Loaded `.agents/skills` + `AGENTS.md` | yes (silently skipped a skill whose frontmatter was invalid YAML; fixed in the fixture) | yes |
| Followed brief -> plan -> build -> QA | no: ignored AGENTS.md, fixed directly | no: wrote all four log lines in one command up front, never ran QA |
| Fixed the basic bug (`test_basic`) | yes (run `openhands2`) | no: never used its edit tool, ~15 failing BSD `sed -i` attempts, then gave up |
| QA found the spec gap and looped back | no | no |
| Asked the human | no | no |
| Metrics with no extra code | 17 LLM calls, 121k in / 9.5k out tokens | 270k in / 8.4k out tokens, per-turn usage, context window |
| Wall time | 568 s | 497 s |

Raw outputs: `results/<run>/{meta,result,eval}.json`. Run `openhands` (first attempt) failed on a model quirk, see below.

## Local-model gotchas found
- **OpenHands:** with project skills loaded and `reasoning_effort="none"`, qwen3 returned empty replies on every turn
  (80 corrective nudges, `MaxIterationsReached`). `harness/oh_probe.py` isolated it: no skills + reasoning off works,
  skills + reasoning on works. The rerun (`openhands2`) leaves reasoning on.
- **Codex:** `-m qwen3-14b-oh` triggered a model pull ("file does not exist"); `qwen3-14b-oh:latest` works.
  `codex exec` defaults to a read-only sandbox (use `workspace-write`). It assumed a 258k context window for the local
  model; the harness sets `model_context_window=32768`.
- Both: the Codex sandbox blocks network, so tests run from a pre-built offline venv (`pyenv/bin/python -m pytest`).

## Conclusion and limits
- Wiring works on both at $0: local model, repo skills, token metrics, ~30 lines of glue.
- qwen3:14b cannot hold a multi-step prompt-defined process on either harness, so this run cannot rank the harnesses on
  the thing that matters (the natural build -> QA -> re-plan loop). The human relay is unproven on both because neither
  model chose to ask.
- Single run per harness; results are anecdotal.

## Reproduce
Scripts use absolute paths under `/private/tmp/claude-501/bake/` (scratch on the original machine). Recreate: an Ollama
model `qwen3-14b-oh` (`FROM qwen3:14b`, `num_ctx 32768`), `npm install --prefix <dir> @openai/codex`, a venv with
`openai-codex`, a venv with `openhands-sdk==1.21.0 openhands-tools==1.21.0`, a venv with `pytest`, then `harness/run_all.sh`.

## Next (not done)
- ~~Stronger free local model on both harnesses~~ done in rounds 2-3 (qwen3.8:27b instead of gpt-oss:20b).
- ~~A ticket that explicitly requires asking the product owner~~ done in rounds 2-3.
- ~~A QA-only requirement to force the QA -> brief loop-back~~ done in round 4 (OpenHands, passed).
- Claude Agent SDK deferred: the owner will not use a Claude key until the setup is better defined.

## Rounds 2-3: qwen3.8:27b (2026-10-21)

Model chosen by a separate local-LLM benchmark (`~/llm-compare/RESULTS.md` on the original machine): `qwen3.8:27b`
Q4_K_M, run here as `qwen3.8-27b-32k` (`harness/Modelfile.qwen38-32k`, `num_ctx 32768`). Runs under
`caffeinate -dimsu`, one model process at a time, gated on the benchmark's `STATUS.txt`.

Changes from round 1: model; `max_output_tokens` 4096 -> 8192 (the benchmark saw a qwen3.8 reply truncated at 2048);
the ticket now explicitly requires asking the product owner before building, to prove ask -> wait -> resume.

**Round 2 (one run each, strict `QUESTION:` relay):** Codex passed everything (asked, resumed, implemented "return 0",
QA PASS, 3/3 hidden tests). OpenHands wrote a correct brief and paused for the decision, but phrased it as
"I'm pausing per the QUESTION protocol" without the exact `QUESTION:` line, so the strict relay missed it (0/3).

**Round 3 (3 trials each, same tolerant relay for both):** `find_question()` in both harnesses accepts the exact line or
a reply that says it is pausing for the question protocol.

| Trial | Time | Asked | Resumed and finished | Hidden tests | QA verdict | Tokens in |
|---|---|---|---|---|---|---|
| OpenHands 1 | 383 s | yes | yes | 3/3 | PASS | 157k |
| OpenHands 2 | 488 s | yes | yes | 3/3 | PASS | 159k |
| OpenHands 3 | 744 s | yes | yes | 3/3 | PASS | 254k |
| Codex 1 | 340 s | yes | yes | 3/3 | PASS | 121k |
| Codex 2 | 580 s | yes | yes | 3/3 | PASS | 271k |
| Codex 3 | 730 s | yes | yes | 3/3 | PASS | 233k |

Raw outputs: `results/r2-*`, `results/r3-<harness>-<trial>`.

**Findings**
- On qwen3.8:27b both harnesses follow the prompt-defined process, catch the spec requirement, ask the human, resume the
  same session with the answer and pass all hidden tests. Tied on behaviour.
- QA loop-back is still **untested**: every brief caught the `None` requirement up front (the agents read
  `docs/spec.md` while briefing), so QA never had a gap to send back. Codex trial 2 ran QA three times, but as repeated
  checks, not a return to the brief. A fixture with a QA-only checklist is needed to force it.
- Swap grew from 8.0 to 18 GB across the six back-to-back runs and later trials ran slower (383 s -> 744 s); the slowdown
  across trials is likely memory pressure rather than the harnesses (not measured directly).

**Decision:** OpenHands (ADR 0005). Deciding factor: Codex's built-in Bedrock provider officially supports only OpenAI GPT
models (OpenAI help article "Configure Codex with Amazon Bedrock", checked 2026-10-21), while OpenHands reaches any
model via litellm, including Claude on Bedrock (untested here). Accepted cost: OpenHands has no built-in command sandbox
on the host, so it must run inside Docker.

## Round 4: QA loop-back (2026-10-22)

`fixture-qa/` adds `qa/checklist.md` with a requirement only the QA step reads (results rounded to 2 decimal places;
`average([1, 2, 2])` is `1.67`). `AGENTS.md` says only qa-review opens `qa/`. Hidden tests: `hidden/test_hidden_qa.py`
(round 3's three tests plus `test_rounds_two_dp`). OpenHands only (the chosen harness), qwen3.8-27b-32k, one run.

Result (`results/r4-openhands/`, including the agent's own `log.md`, `qa.md` and `brief.md`):

```
ignite-brief  caught None requirement from spec; empty-list behaviour pending PO decision
  QUESTION -> product owner: return 0 -> resumed
ignite-brief  updated with PO decision
ignite-plan -> ignite-build  tests pass
qa-review     GAP - checklist requires rounding to 2 dp; brief missed it
ignite-brief  revised after QA - added rounding requirement
ignite-plan -> ignite-build  round(..., 2)
qa-review     loop 1 VERDICT: PASS
```

Hidden tests 4/4, `test_calc.py` untouched, 690 s, 31 LLM calls, 379k in / 7k out tokens. The loop came from
`AGENTS.md` and the skills alone; the harness has no orchestration code. Single run.

## Round 5: Flint 40B on round 4 (2026-10-24)

Recursive's Flint (`flint:40b`, 39.8B MoE with about 2.5B active, released 2026-10-21) as `flint-32k`
(`harness/Modelfile.flint-32k`: `num_ctx 32768`, temperature 1, top_k 20, top_p 0.95). Same fixture, ticket, answer and
harness as round 4 (`harness/run_round5.sh`; the model is set through `BAKE_MODEL`). Ollama 0.40.9 (MLX backend; round 4
ran on 0.33.1). One run.

| | Round 4: qwen3.8-27b-32k | Round 5: flint-32k |
|---|---|---|
| Asked the product owner, resumed | yes | yes |
| Hidden tests | 4/4 | 4/4 |
| `test_calc.py` untouched | yes | yes |
| QA loop-back (GAP, then brief revised) | yes | **no** |
| Read `qa/` outside qa-review | no | **yes**: brief says "rounded to 2 decimal places (per QA checklist)" |
| Wall time | 690 s | **194 s** |
| LLM calls, input tokens | 31, 379k | 21, 219k |

Flint produced the right code 3.6 times faster, but broke the `AGENTS.md` rule that only qa-review opens `qa/`, so the
loop-back this round tests never happened. That is a process failure even though the hidden tests pass: on a real repo
it means a step ignoring its instructions. Swap was about 17 GB at the end; the separate benchmark saw Flint grow swap by
10.3 GB and called it too big to run comfortably beside other apps on 32 GB. Results in `results/r5-flint-openhands/`.
Verdict: qwen3.8 stays the default; Flint is a speed candidate if a stricter prompt or a repeat run shows it follows
the process.

**Control: qwen3.8 rerun on Ollama 0.40.9 (2026-10-24).** Round 4 repeated unchanged, to separate the model from the
Ollama upgrade. `ollama ps` showed qwen3.8 on the `llamacpp` runner (not MLX). Result: asked and resumed, QA GAP then
brief revised and rebuilt, QA PASS, hidden 4/4, `test_calc.py` untouched. 426 s (was 690 s on 0.33.1), 32 LLM calls,
366k in / 5.6k out tokens. Results in `results/r4b-openhands-ollama0409/`. So the upgrade alone made qwen3.8 about 1.6
times faster on this run, and Flint's remaining lead over it is about 2.2 times (194 s against 426 s). One run each.
