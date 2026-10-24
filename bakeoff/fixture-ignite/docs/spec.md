# Product spec: calc

## average(numbers)
Shipped. Mean of the numbers, None values ignored, rounded to 2 decimal places, 0 for an empty list.

## median(numbers) (new)
- Returns the median of the numbers.
- **None values must be ignored**, as in average(). `median([1, None, 3])` is 2.
- For an even count, the median is the mean of the two middle values. `median([4, 1, 3, 2])` is 2.5.
- Behaviour for an empty list (or a list of only None values) is a **product decision**: the product owner must be asked. Do not guess.
