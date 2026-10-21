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
- A QA-only requirement to force the QA -> brief loop-back (still untested).
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
