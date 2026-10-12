"""Codex's estimates for the third-quarter replication: checked before each report, scored after it.

An estimate gives, for every threshold of a ladder, the chance that the reported figure is above it. It must be filed
before midnight New York time at the start of the report's date, the moment the market's prices are read, so both
use no information the other lacks.
"""

from datetime import datetime, time
from zoneinfo import ZoneInfo

from .read import check_citation

NEW_YORK = ZoneInfo("America/New_York")


def check_estimate(estimate, open_ladders, sources, replay=None):
    """An estimate that passes every rule, or a ValueError naming the first it breaks."""
    ladder = next((x for x in open_ladders if x["ladder"] == estimate.get("ladder")), None)
    if ladder is None:
        raise ValueError(f"{estimate.get('ladder')} is not an open third-quarter ladder")
    chances = sorted(estimate.get("chances") or [], key=lambda c: c["strike"])
    if [c["strike"] for c in chances] != sorted(ladder["thresholds"]):
        raise ValueError("Give a chance for every threshold of the ladder, once each")
    values = [c["above"] for c in chances]
    if any(not isinstance(v, (int, float)) or isinstance(v, bool) or not 0 <= v <= 1 for v in values):
        raise ValueError("Each chance must be a number between 0 and 1")
    if any(a < b for a, b in zip(values, values[1:])):
        raise ValueError("The chances must fall as the threshold rises")
    deadline = datetime.combine(datetime.fromisoformat(estimate["report_date"]).date(), time(0), tzinfo=NEW_YORK)
    if datetime.fromisoformat(estimate["filed_at"]) > deadline:
        raise ValueError("File the estimate before midnight New York time at the start of the report's date")
    if not str(estimate.get("method") or "").strip():
        raise ValueError("State the method that turns the inputs into chances")
    checked = [check_citation(c, sources, replay) for c in estimate.get("inputs") or []]
    return {**estimate, "chances": chances, "inputs": checked}


def crps(chances, strikes, outcomes):
    """The continuous ranked probability score over a ladder's thresholds: each squared gap between a chance of being
    above a threshold and the outcome, weighted by the distance to the next threshold; lower is better."""
    gaps = [b - a for a, b in zip(strikes, strikes[1:])]
    weights = gaps + [gaps[-1] if gaps else 1]
    return sum((p - o) ** 2 * w for p, o, w in zip(chances, outcomes, weights))
