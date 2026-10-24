# Brief: average() in calc.py

## Problem
`average()` returns the wrong value: it divides by `len(numbers) + 1` instead of the actual number of values, so `average([2, 4, 6])` computes `12 / 4 = 3` instead of `4`.

## Requirements
- `average(numbers)` returns the arithmetic mean of the numbers.
- `average([2, 4, 6])` must be `4`.
- `None` values in the list must be ignored (missing readings, not zeros). `average([2, None, 4])` is `3`.

## Acceptance criteria
- `average([2, 4, 6]) == 4`.
- `average([2, None, 4]) == 3`.
- Results rounded to 2 decimal places (per QA checklist): `average([1, 2, 2])` is `1.67`.

## Open decisions
- Behaviour for an empty list (or list of only `None` values) is an unresolved product decision (see `docs/spec.md`); must be asked before building.