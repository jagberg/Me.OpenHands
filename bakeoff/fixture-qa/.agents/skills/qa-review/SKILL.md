---
name: qa-review
description: "Check the implementation against docs/spec.md and the brief; report PASS or GAP."
---
# qa-review
Read docs/spec.md, `qa/checklist.md`, `.ignite/brief.md` and the code. For every requirement in docs/spec.md and qa/checklist.md, check the brief covers it and the code implements it.
Write `.ignite/qa.md` with one line per requirement (covered / GAP) and a final line `VERDICT: PASS` or `VERDICT: GAP`.
If any requirement needs a product decision that nobody has answered yet, ask it with the QUESTION protocol in AGENTS.md.
