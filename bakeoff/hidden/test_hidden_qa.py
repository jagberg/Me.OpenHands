from calc import average


def test_basic():
    assert average([2, 4, 6]) == 4


def test_ignores_none():          # requirement only in docs/spec.md (QA should catch the gap)
    assert average([2, None, 4]) == 3


def test_empty_is_zero():         # the human's answer will be "return 0"
    assert average([]) == 0
    assert average([None]) == 0


def test_rounds_two_dp():         # requirement only in qa/checklist.md (QA must send the agent back to the brief)
    assert average([1, 2, 2]) == 1.67
