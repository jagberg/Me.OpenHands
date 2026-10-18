# ignite-plan (dummy)
Read `.ignite/brief.md`, then write `.ignite/plan.md`.
Headings: `# Plan`, `## Root cause` (file and line), `## Change` (smallest fix), `## Verification`.
Do NOT change source or test files in this stage. When the file exists, call finish with one sentence.

## Asking a human (optional)
If you need a human decision, write `.ignite/QUESTION.md` (inside the working folder). First line is either
`BLOCKING: <question>` (you cannot proceed safely without the answer) or `ASK: <question>` followed by a line `ASSUMPTION: <what you will do meanwhile>`.
Ask at most one question, and never re-ask anything listed under "Decisions so far".
