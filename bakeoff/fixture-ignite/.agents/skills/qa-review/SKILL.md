---
name: qa-review
description: "Check the implementation against docs/spec.md and the approved brief; report PASS or GAP."
---
# qa-review
Read docs/spec.md, the brief in `intent/<feature-name>/brief.md`, the OpenSpec change and the code. For every requirement
in docs/spec.md, check the brief covers it and the code implements it, and that the tests pass.
Write `.ignite/qa.md` with one line per requirement (covered / GAP) and a final line `VERDICT: PASS` or `VERDICT: GAP`.
If any requirement needs a product decision that nobody has answered yet, ask it with the QUESTION protocol in AGENTS.md.
