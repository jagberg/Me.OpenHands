# Harness bake-off: OpenHands SDK vs Codex SDK (2026-10-19)

Same fixture, same ticket, same scripted human answer, same local model (Ollama `qwen3-14b-oh`, qwen3:14b with 32k
context). No Claude or OpenAI key, $0. The process is defined only in prompts (`fixture/AGENTS.md` and
`fixture/.agents/skills/*/SKILL.md`); each harness only starts the agent and relays a `QUESTION:` line to a scripted
product owner. Rationale: ADR 0005 (proposed).

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
- Stronger free local model (`gpt-oss:20b`, ~13 GB) on both harnesses.
- A ticket that explicitly requires asking the product owner, to prove ask -> wait -> resume wiring independent of model judgement.
- Claude Agent SDK deferred: the owner will not use a Claude key until the setup is better defined.
