# ignite-build (dummy)
Follow `.ignite/plan.md` and every item under "Decisions so far". Change source files only; never edit existing tests. Remove stale comments you make obsolete.
For EVERY item under "Decisions so far", create or update `test_decisions.py` (in the working folder) with a pytest test that encodes that decision exactly, then implement it.
Run the test command and confirm everything passes. Never run git commit or git push. Finish with 2-3 sentences: root cause, the change, test result.
