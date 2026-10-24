# Brief: average() returns wrong value

## Problem
`average([2, 4, 6])` returns 3.0 instead of 4. The implementation divides by `len(numbers) + 1` instead of the number of values. Additionally, the spec requires `None` values to be ignored, but the current code crashes on them (and would count them as zeros if it didn't).

## Requirements
- `average(numbers)` returns the arithmetic mean of the numbers in the list.
- `None` values in the list are ignored (missing readings, not zeros): `average([2, None, 4]) == 3`.
- An empty list, or a list of only `None` values, returns **0** (product owner decision — do not raise).
- Results are rounded to **2 decimal places** (revised after QA): `average([1, 2, 2]) == 1.67`.

## Acceptance criteria
- `average([2, 4, 6]) == 4`
- `average([2, None, 4]) == 3`
- `average([]) == 0` and `average([None, None]) == 0` (no exception).
- `average([1, 2, 2]) == 1.67` (rounded to 2 decimal places).
- Existing test suite passes: `python -m pytest -q`.

## Open decisions
- (resolved) Empty / all-None list returns 0 — decided by product owner.
