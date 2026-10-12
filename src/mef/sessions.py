"""Regular NYSE sessions, with holidays, from 2023 to 2027."""

from datetime import date
from functools import lru_cache


@lru_cache(maxsize=1)
def calendar():
    import exchange_calendars as xcals

    sessions = xcals.get_calendar("XNYS", start="2023-01-01", end="2027-12-31").sessions
    return [s.date().isoformat() for s in sessions]


@lru_cache(maxsize=1)
def positions():
    return {day: i for i, day in enumerate(calendar())}


def iso(day):
    return day.isoformat() if isinstance(day, date) else day


def is_session(day):
    return iso(day) in positions()


def next_session(day):
    """The first session after a day, whether or not the day is a session."""
    day = iso(day)
    return next(s for s in calendar() if s > day)


def offset(day, n):
    """The session n sessions after a session day; n can be negative."""
    i = positions()[iso(day)] + n
    if not 0 <= i < len(calendar()):
        raise ValueError(f"{iso(day)} plus {n} sessions is outside the calendar")
    return calendar()[i]
