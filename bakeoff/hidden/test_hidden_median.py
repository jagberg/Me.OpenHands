from calc import average, median


def test_average_unchanged():
    assert average([2, 4, 6]) == 4


def test_odd():
    assert median([3, 1, 2]) == 2


def test_even():
    assert median([4, 1, 3, 2]) == 2.5


def test_ignores_none():
    assert median([1, None, 3]) == 2


def test_empty_is_none():  # product owner answer used in the factory test: return None
    assert median([]) is None and median([None]) is None
