---
name: qa-review
description: "Check the implementation against the approved brief and the OpenSpec change; report PASS or GAP."
---
# qa-review
Read the approved brief in `intent/<feature-name>/brief.md`, the OpenSpec change (proposal, specs, tasks) and the code.
For every requirement in the brief and every scenario in the change's specs, check the code implements it and a test
covers it, and run the test command from `knowledge/project.md`.
Write `.ignite/qa.md` with one line per requirement (covered / GAP) and a final line `VERDICT: PASS` or `VERDICT: GAP`.
If any requirement needs a product decision that nobody has answered yet, ask it with the QUESTION protocol in AGENTS.md.
