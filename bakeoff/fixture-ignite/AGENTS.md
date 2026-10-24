# How to work in this repo (the ignite process)

You are running unattended in a software factory. Work through these steps in order:

1. `brief` skill (ignite:brief): write the PRD as a local file, `intent/<feature-name>/brief.md`, `Status: draft`.
2. Human approval of the brief. Ask: `QUESTION: Brief ready at intent/<feature-name>/brief.md. Approve it?` The factory
   sets `Status: approved` when the human approves. Never write `approved` yourself. If the human asks for changes,
   revise the brief and ask again.
3. `plan` skill (ignite:plan): the engine is in `knowledge/calc.md`. `opsx:propose` means the `openspec-propose` skill.
4. `build` skill (ignite:build): its design-review question is a QUESTION too. `opsx:apply` means the
   `openspec-apply-change` skill, which implements the tasks.
5. `qa-review` skill. If it reports a GAP, go back to the step that missed it, then build and QA again. At most 2 loops.

Talking to humans:
- The skills say "ask the user". In this repo the only human is the product owner, reached only like this: stop working
  and end your reply with exactly one line `QUESTION: <one question>`. The answer arrives in the next message; then
  continue from where you stopped. One question per reply.
- Settings the skills would ask about are already decided in `knowledge/calc.md` (PRD destination, spec engine). Do not
  ask about them, and do not ask to confirm before writing a file.

House rules:
- Append one line to `.ignite/log.md` at the start of every step: `<step name>: <one-line note>`.
- The OpenSpec CLI: if `openspec` is missing, run `npm install -g @fission-ai/openspec@1.15.0`.
- Run tests with `python3 -m pytest -q` (`pip install pytest` if missing). Never edit test_calc.py; add new tests in
  new files. Never run git commit or git push.
- When QA passes, finish with a 3-line summary: what changed, which human decisions were applied, where the PRD and
  OpenSpec change are.
