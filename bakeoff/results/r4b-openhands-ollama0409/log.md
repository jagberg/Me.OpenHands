ignite-brief: initial brief for average() bug from ticket + docs/spec.md
ignite-brief: updated with product owner decision (empty/all-None list returns 0, no raise)
ignite-plan: plan written — filter Nones, return 0 when empty, divide by real count
ignite-build: implementing average() fix per plan
ignite-build: fixed average() (filter Nones, 0 when empty); pytest passed + manual checks OK
qa-review: reviewing spec, checklist, brief and code
ignite-brief: revised after QA GAP — added 2-decimal rounding requirement
ignite-plan: updated plan — round result to 2 decimals
ignite-build: adding round(..., 2) to average()
ignite-build: rounding added; pytest + manual checks passed
qa-review: re-review after gap fix
