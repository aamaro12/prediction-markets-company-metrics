"""The analysis plan's tests, run once on the frozen events.

Intervals come from bootstrap resamples that draw results dates, not events, so events reported on 1 day move
together. The seed is fixed, so a rerun gives the same intervals.
"""

import random
import statistics

SEED = 20261012
RESAMPLES = 10_000
MIN_EVENTS = 100


def usable(events, key):
    return [e for e in events if e["outcome"] in ("beat", "miss") and e["returns"].get(key) is not None]


def gap(rows, key):
    beats = [e["returns"][key] for e in rows if e["outcome"] == "beat"]
    misses = [e["returns"][key] for e in rows if e["outcome"] == "miss"]
    return statistics.fmean(beats) - statistics.fmean(misses) if beats and misses else None


def by_date(rows):
    dates = {}
    for e in rows:
        dates.setdefault(e["results_day"], []).append(e)
    return dates


def interval(draws):
    draws = sorted(draws)
    return draws[int(0.025 * len(draws))], draws[int(0.975 * len(draws)) - 1]


def bootstrap_difference(events, key, resamples=RESAMPLES, seed=SEED):
    """The mean return after beats minus after misses, its 95% interval, and the smallest gap it can reliably detect,
    2.8 standard errors."""
    rows = usable(events, key)
    dates = by_date(rows)
    days = sorted(dates)
    rng = random.Random(seed)
    draws = []
    for _ in range(resamples):
        sample = [e for d in (rng.choice(days) for _ in days) for e in dates[d]]
        value = gap(sample, key)
        if value is not None:
            draws.append(value)
    low, high = interval(draws) if draws else (None, None)
    se = statistics.stdev(draws) if len(draws) > 1 else None
    return {
        "n": len(rows),
        "dates": len(days),
        "beats": sum(e["outcome"] == "beat" for e in rows),
        "misses": sum(e["outcome"] == "miss" for e in rows),
        "difference": gap(rows, key),
        "low": low,
        "high": high,
        "se": se,
        "detectable": 2.8 * se if se is not None else None,
    }


def accuracy(ladder_rows):
    """How far the market's expected figure was from the reported one, as a share of the reported figure, and how often
    the reported figure fell inside the market's 25th to 75th percentiles."""
    rows = [r for r in ladder_rows if r.get("excluded") is None and r.get("figure") is not None and r.get("expected")]
    shares = [abs(r["figure"] - r["expected"]["median"]) / abs(r["figure"]) for r in rows if r["figure"]]
    spread = [r for r in rows if r["expected"].get("q25") is not None and r["expected"].get("q75") is not None]
    return {
        "n": len(rows),
        "median_gap_share": statistics.median(shares) if shares else None,
        "with_spread": len(spread),
        "inside_spread": sum(r["expected"]["q25"] <= r["figure"] <= r["expected"]["q75"] for r in spread),
    }


def direction(events):
    rows = usable(events, "results_day")
    beats = [e for e in rows if e["outcome"] == "beat"]
    misses = [e for e in rows if e["outcome"] == "miss"]
    return {
        "beats": len(beats),
        "beats_up": sum(e["returns"]["results_day"] > 0 for e in beats),
        "misses": len(misses),
        "misses_down": sum(e["returns"]["results_day"] < 0 for e in misses),
    }


def ranks(values):
    order = sorted(range(len(values)), key=lambda i: values[i])
    result = [0.0] * len(values)
    i = 0
    while i < len(order):
        j = i
        while j + 1 < len(order) and values[order[j + 1]] == values[order[i]]:
            j += 1
        for k in range(i, j + 1):
            result[order[k]] = (i + j) / 2 + 1  # tied values share their average rank
        i = j + 1
    return result


def spearman(x, y):
    """The rank correlation, or None when either input is constant."""
    try:
        return statistics.correlation(ranks(x), ranks(y))
    except statistics.StatisticsError:
        return None


def spread_and_move(events):
    """The rank correlation between the spread, as a share of the expected figure, and the absolute results-day move."""
    rows = [
        e
        for e in events
        if e["returns"].get("results_day") is not None and e["expected"].get("spread") and e["expected"]["median"]
    ]
    if len(rows) < 3:
        return {"n": len(rows), "rank_correlation": None}
    x = [e["expected"]["spread"] / abs(e["expected"]["median"]) for e in rows]
    y = [abs(e["returns"]["results_day"]) for e in rows]
    return {"n": len(rows), "rank_correlation": spearman(x, y)}


def slope(events, resamples=RESAMPLES, seed=SEED):
    """The least-squares slope of results-day returns on the standardised surprise, with its 95% interval."""
    rows = [e for e in events if e.get("standardised") is not None and e["returns"].get("results_day") is not None]

    def fit(sample):
        x = [e["standardised"] for e in sample]
        if len(sample) < 3 or len(set(x)) < 2:
            return None
        return statistics.linear_regression(x, [e["returns"]["results_day"] for e in sample]).slope

    dates = by_date(rows)
    days = sorted(dates)
    rng = random.Random(seed)
    draws = [
        v
        for v in (fit([e for d in (rng.choice(days) for _ in days) for e in dates[d]]) for _ in range(resamples))
        if v is not None
    ]
    low, high = interval(draws) if draws else (None, None)
    return {"n": len(rows), "slope": fit(rows), "low": low, "high": high}


def study(events, ladder_rows, resamples=RESAMPLES):
    """Every test in the plan, and its stopping rules: accuracy only below 100 events, and no measurable difference when
    the primary interval includes 0."""
    result = {"events": len(events), "accuracy": accuracy(ladder_rows)}
    if len(usable(events, "results_day")) < MIN_EVENTS:
        return {**result, "conclusion": "fewer than 100 events: accuracy only"}
    primary = bootstrap_difference(events, "results_day", resamples)
    result.update(
        primary=primary,
        secondary={
            "two_sessions": bootstrap_difference(events, "two_sessions", resamples),
            "direction": direction(events),
            "spread_and_move": spread_and_move(events),
        },
        exploratory={
            "drift_20": bootstrap_difference(events, "drift_20", resamples),
            "drift_60": bootstrap_difference(events, "drift_60", resamples),
            "slope": slope(events, resamples),
        },
        conclusion="no measurable difference" if primary["low"] <= 0 <= primary["high"] else "measured difference",
    )
    return result
