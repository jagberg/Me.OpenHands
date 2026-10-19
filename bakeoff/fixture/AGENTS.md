# How to work in this repo (the ignite process)

Work through these skills in order, each one a separate step: ignite-brief, then ignite-plan, then ignite-build, then qa-review.

- Append one line to `.ignite/log.md` at the start of every step: `<step name>: <one-line note>`.
- If qa-review reports a GAP (a requirement in docs/spec.md that the brief missed), go back to ignite-brief, update the brief,
  then plan, build and QA again. At most 2 loops.
- When something needs a human decision, do not guess. Stop working and end your reply with exactly one line:
  `QUESTION: <your question>`. You will get the answer in the next message; then continue from where you stopped.
- Never edit test_calc.py. Never run git commit or git push. Run tests with: `/private/tmp/claude-501/bake/pyenv/bin/python -m pytest -q` (works offline).
- When QA passes, finish with a 3-line summary: what was wrong, what changed, which human decisions were applied.
