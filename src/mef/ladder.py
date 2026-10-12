"""The market's expected figure from a ladder's prices.

Each threshold X prices the chance, in percent, that the reported figure is above X. Those chances must fall as X rises;
where trading leaves them out of order, adjacent thresholds are pooled to their average until they fall (isotonic
regression). The figure's quantiles are then read by linear interpolation between the 2 thresholds that bracket them.
"""


def falling(prices):
    """The closest sequence that never rises, pooling out-of-order neighbours to their average."""
    blocks = []  # [sum, count]
    for p in prices:
        blocks.append([p, 1])
        while len(blocks) > 1 and blocks[-2][0] / blocks[-2][1] < blocks[-1][0] / blocks[-1][1]:
            total, count = blocks.pop()
            blocks[-1][0] += total
            blocks[-1][1] += count
    return [total / count for total, count in blocks for _ in range(count)]


def quantile(points, q):
    """The figure with a chance q of being at or below it: where the chance of being above it falls to 1 - q.

    points are (threshold, chance above in percent). None when the target lies beyond the priced thresholds."""
    points = sorted(points)
    if len(points) < 2:
        return None
    strikes = [x for x, _ in points]
    chances = falling([p for _, p in points])
    target = (1 - q) * 100
    if chances[0] < target or chances[-1] > target:
        return None
    at = [i for i, p in enumerate(chances) if p == target]
    if at:  # exactly at the target, possibly along a flat stretch: its middle
        return (strikes[at[0]] + strikes[at[-1]]) / 2
    i = next(i for i in range(len(chances) - 1) if chances[i] > target > chances[i + 1])
    return strikes[i] + (chances[i] - target) / (chances[i] - chances[i + 1]) * (strikes[i + 1] - strikes[i])


def expected_figure(points):
    """The market's median figure and its spread, the 25th to 75th percentile, read from the priced thresholds; None
    when the median falls outside them, as when every priced threshold sits on 1 side of 50%."""
    points = [(x, p) for x, p in points if p is not None]
    median = quantile(points, 0.5)
    if median is None:
        return None
    q25, q75 = quantile(points, 0.25), quantile(points, 0.75)
    return {
        "median": median,
        "q25": q25,
        "q75": q75,
        "spread": q75 - q25 if q25 is not None and q75 is not None else None,
    }


def surprise(figure, expected):
    """A beat or a miss of the market's median; equal figures are neither. Standardised by the spread when known."""
    gap = figure - expected["median"]
    outcome = "beat" if gap > 0 else "miss" if gap < 0 else None
    spread = expected.get("spread")
    return {"outcome": outcome, "standardised": gap / spread if spread else None}
