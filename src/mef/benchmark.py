"""The market's expected figure against 2 simple forecasts, outside the plan: the same quarter a year earlier, and the
quarter before. Codex cites each earlier figure from the company's own publications; Python checks every citation and
compares the forecasts on the same ladders, with the accuracy test's measure: the gap as a share of the figure."""

import re
import statistics

from .read import check_citation

FORECASTS = ("year_ago", "previous_quarter")
RATE = re.compile(r"\b(growth|comparable|comp|change|same.?(store|restaurant)|margin)\b", re.I)  # by the title


def check_earlier(name, ladder, earlier, sources, replay=None):
    if not str(earlier.get("period") or "").strip():
        raise ValueError(f"{ladder}: {name} needs its period, such as Q2 2025")
    value = earlier.get("value")
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError(f"{ladder}: {name} value must be the figure as a number in the contract's units")
    citation = check_citation(earlier.get("citation"), sources, replay)
    digits = re.sub(r"[^\d.]", "", str(earlier.get("as_published") or ""))
    if not digits or digits not in re.sub(r"[^\d.]", "", citation["excerpt"]):
        raise ValueError(f"{ladder}: the {name} citation does not contain {earlier.get('as_published')}")
    return {**earlier, "citation": citation}


def check_comparative(entry, sources, replay=None):
    """Codex's earlier figures for 1 ladder, each cited, or a refusal with the reason."""
    ladder = entry.get("ladder")
    if not ladder:
        raise ValueError("an entry needs its ladder")
    if not any(entry.get(name) for name in FORECASTS):
        raise ValueError(f"{ladder}: cites neither the year-ago figure nor the quarter before")
    checked = {
        name: check_earlier(name, ladder, entry[name], sources, replay) if entry.get(name) else None
        for name in FORECASTS
    }
    return {**entry, **checked}


def compare(pairs, measure):
    return {
        "n": len(pairs),
        f"market_median_gap_{measure}": statistics.median(m for m, _ in pairs) if pairs else None,
        f"forecast_median_gap_{measure}": statistics.median(f for _, f in pairs) if pairs else None,
        "market_closer": sum(m < f for m, f in pairs),
        "forecast_closer": sum(f < m for m, f in pairs),
        "ties": sum(m == f for m, f in pairs),
    }


def benchmark(ladder_rows, earlier):
    """For each simple forecast, the ladders it covers among those the accuracy test kept, the median gap of the market
    and of the forecast on those same ladders, and how often each came closer. Growth rates and margins are also
    compared in points, since a share of a small rate inflates every gap."""
    kept = [r for r in ladder_rows if r.get("excluded") is None and r.get("figure") and r.get("expected")]
    result = {"kept": len(kept)}
    for name in FORECASTS:
        shares, points = [], []
        for r in kept:
            forecast = (earlier.get(r["ladder"]) or {}).get(name)
            if forecast and forecast.get("value") is not None:
                figure, market, simple = r["figure"], r["expected"]["median"], forecast["value"]
                shares.append((abs(figure - market) / abs(figure), abs(figure - simple) / abs(figure)))
                if RATE.search(r.get("title") or ""):
                    points.append((abs(figure - market), abs(figure - simple)))
        result[name] = {**compare(shares, "share"), "rates": compare(points, "points")}
    return result
