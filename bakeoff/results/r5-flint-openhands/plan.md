# Plan: average() in calc.py

## Root cause
`average()` divides by `len(numbers) + 1` instead of the number of valid values.

## Change
In `calc.py`:
- Filter out `None` values.
- Return `0` if no valid values remain (empty / all-None list; product decision confirmed: return 0, do not raise).
- Return the mean rounded to 2 decimal places.

## Verification
Run: `/private/tmp/claude-501/bake/pyenv/bin/python -m pytest -q`
Expected: `average([2, 4, 6]) == 4`, `average([2, None, 4]) == 3`, `average([1, 2, 2]) == 1.67`.