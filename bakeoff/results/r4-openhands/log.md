ignite-brief: wrote .ignite/brief.md (bug is len+1 divisor; spec adds None-ignoring; empty-list behaviour pending PO decision)
ignite-brief: updated brief with PO decision — empty/all-None lists return 0, do not raise
ignite-plan: wrote .ignite/plan.md (filter None, return 0 if empty, divide by valid count)
ignite-build: fixed calc.py (filter None, return 0 when empty); pytest 1 passed, manual checks OK
qa-review: GAP — checklist requires rounding to 2 dp (average([1,2,2])==1.67); brief missed it
ignite-brief: revised after QA — added rounding-to-2-decimals requirement
ignite-plan: updated plan — return round(mean, 2) per QA checklist (loop 1)
ignite-build: added round(..., 2); pytest 1 passed; manual checks incl. average([1,2,2])==1.67 OK
qa-review: loop 1 VERDICT: PASS — all spec + checklist requirements covered and verified
