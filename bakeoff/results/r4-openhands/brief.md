# Brief: fix average() in calc.py

## Problem
`average([2, 4, 6])` returns 3 instead of 4. The divisor is `len(numbers) + 1`
instead of the count of valid numbers.

## Requirements
- `average(numbers)` returns the arithmetic mean of the numbers.
- None values in the list must be ignored (missing readings, not zeros);
  e.g. `average([2, None, 4]) == 3` (per docs/spec.md).
- Empty list / all-None lists return 0 (product owner decision, 2026-10-22).
- Results are rounded to 2 decimal places; e.g. `average([1, 2, 2]) == 1.67`
  (revised after QA — from qa/checklist.md).

## Acceptance criteria
- `average([2, 4, 6]) == 4`
- `average([2, None, 4]) == 3`
- `average([]) == 0` and `average([None, None]) == 0` (product owner decision;
  must not raise).
- `average([1, 2, 2]) == 1.67` (rounded to 2 decimal places).
- All tests pass via `python -m pytest -q`.

## Open decisions
- (resolved) Empty / all-None list: return 0, do not raise.
