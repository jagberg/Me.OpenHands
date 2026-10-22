# QA review (loop 1)

- Spec: returns arithmetic mean — covered (brief + calc.py; verified average([2,4,6]) == 4).
- Spec: None values ignored, average([2, None, 4]) == 3 — covered (brief + calc.py filters None; verified 3.0).
- Spec: empty/all-None is a product decision, must be asked — covered (PO asked, decided return 0; brief records decision; calc.py returns 0; verified).
- Checklist: results rounded to 2 decimal places, average([1, 2, 2]) == 1.67 — covered (brief revised after QA; calc.py uses round(..., 2); verified 1.67).

VERDICT: PASS
