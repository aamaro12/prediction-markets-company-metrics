"""The plan's 10 largest results-day moves against the surprise: a beat followed by a fall, or a miss by a rise. Codex
explains each from news, and Python checks that every passage is at its locator in a document published by the end of
results day in New York, so no explanation leans on hindsight."""

from datetime import datetime, time, timedelta

from .events import NEW_YORK
from .fetching import timestamp
from .read import check_citation

LARGEST = 10


def against_surprise(events, n=LARGEST):
    """The n largest results-day moves against the surprise, largest first; a tie goes by ladder."""
    rows = [
        e
        for e in events
        if e["returns"].get("results_day") is not None
        and (
            (e["outcome"] == "beat" and e["returns"]["results_day"] < 0)
            or (e["outcome"] == "miss" and e["returns"]["results_day"] > 0)
        )
    ]
    return sorted(rows, key=lambda e: (-abs(e["returns"]["results_day"]), e["ladder"]))[:n]


def check_explanation(entry, event, sources, replay=None):
    """Codex's explanation of 1 move, with each citation found at its locator and published by the end of results day."""
    ladder = entry.get("ladder")
    if not str(entry.get("explanation") or "").strip():
        raise ValueError(f"{ladder}: needs its explanation")
    if not entry.get("citations"):
        raise ValueError(f"{ladder}: needs a citation")
    end = datetime.combine(datetime.fromisoformat(event["results_day"]).date(), time(0), tzinfo=NEW_YORK)
    end += timedelta(days=1)
    checked = []
    for citation in entry["citations"]:
        c = check_citation(citation, sources, replay)
        if not c.get("published_at"):
            raise ValueError(f"{ladder}: {c['url']} records no publication time")
        if timestamp(c["published_at"]) >= end:
            raise ValueError(f"{ladder}: {c['url']} was published after results day")
        checked.append(c)
    return {
        **entry,
        "citations": checked,
        "company": event["company"],
        "results_day": event["results_day"],
        "outcome": event["outcome"],
        "move": event["returns"]["results_day"],
    }
