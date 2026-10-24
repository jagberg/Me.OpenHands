def average(numbers):
    """Return the arithmetic mean of a list of numbers, ignoring None."""
    values = [n for n in numbers if n is not None]
    return round(sum(values) / len(values), 2) if values else 0
