"""Events: 1 per company and results day, with the market's expected figure, the reported figure and the share's
returns net of SPY, or the reason it is excluded. Every rule here is the analysis plan's."""

from datetime import datetime, time, timezone
from zoneinfo import ZoneInfo

from .kalshi import agrees, close_before
from .ladder import expected_figure, surprise
from .sessions import is_session, next_session, offset

NEW_YORK = ZoneInfo("America/New_York")
CLOSE = time(16, 0)
MIN_DOLLAR_VOLUME = 20_000_000


def results_day(report_time):
    """The session whose close follows the report: that day for a release before 16:00 New York time on a session
    day, which covers before the open and, by addendum 1, during the session; otherwise the next session."""
    local = report_time.astimezone(NEW_YORK)
    day = local.date().isoformat()
    return day if is_session(day) and local.time() < CLOSE else next_session(day)


def cutoff(report_time):
    """Midnight New York time at the start of the report's date, as a UTC timestamp: no price read at or before it can
    follow the report."""
    local = report_time.astimezone(NEW_YORK)
    midnight = datetime.combine(local.date(), time(0), tzinfo=NEW_YORK)
    return int(midnight.astimezone(timezone.utc).timestamp())


def change(closes, start, end):
    a, b = (closes.get(day, {}).get("close") for day in (start, end))
    return b / a - 1 if a and b else None


def market_returns(share, spy, day):
    """The share's return minus SPY's over the same sessions: results day, 2 sessions, and drift after results day."""

    def net(start, end):
        s, m = change(share, start, end), change(spy, start, end)
        return s - m if s is not None and m is not None else None

    def shifted(n):
        try:
            return offset(day, n)
        except ValueError:
            return None

    before = shifted(-1)
    return {
        "results_day": net(before, day),
        "two_sessions": net(before, shifted(1)),
        "drift_20": net(day, shifted(20)),
        "drift_60": net(day, shifted(60)),
    }


def liquidity(share, day):
    """The average dollar volume over the 20 sessions before results day, or None when any is missing."""
    days = [offset(day, -n) for n in range(1, 21)]
    rows = [share.get(d) for d in days]
    if any(r is None for r in rows):
        return None
    return sum(r["close"] * r["volume"] for r in rows) / 20


def price_ladder(ladder, rung_candles, at):
    """Each threshold priced at the last daily close at or before the cutoff, and the ladder's expected figure."""
    priced = {r["ticker"]: close_before(rung_candles.get(r["ticker"], []), at) for r in ladder["rungs"]}
    points = [(r["strike"], (priced[r["ticker"]] or {}).get("price")) for r in ladder["rungs"]]
    return {
        "expected": expected_figure(points),
        "traded_10_days": sum((p or {}).get("traded_10_days", 0) for p in priced.values()),
        "traded_30_days": sum((p or {}).get("traded_30_days", 0) for p in priced.values()),
        "bases": sorted({p["basis"] for p in priced.values() if p and p["basis"]}),
    }


def reported_figure(ladder, verification):
    """The figure the ladder settled on: the venue's, in the thresholds' units, or where the venue states only a bound,
    the figure Codex cites from the company's release, which must agree with every threshold's settlement."""
    if ladder["figure"] is not None:
        return ladder["figure"]
    value = verification.get("figure_value")
    if value is None or not all(agrees(value, r["strike"], r["comparison"], r["result"]) for r in ladder["rungs"]):
        return None
    return value


def universe(entry, report_time, day):
    """Why a company falls outside the universe on its report date, or None."""
    if not entry:
        return "no ticker reference"
    if entry.get("outside_universe"):
        return entry["outside_universe"]
    listed = (entry.get("reference") or {}).get("list_date")
    if listed and listed > report_time.astimezone(NEW_YORK).date().isoformat():
        return "listed after the report"
    traded = liquidity(entry.get("bars") or {}, day)
    if traded is None or traded < MIN_DOLLAR_VOLUME:
        return "below $20m a day"
    return None


def check_ladder(ladder, verification, candles, prices):
    """1 ladder priced at its cutoff, with its reported figure, and the first exclusion that applies, if any."""
    row = {"ladder": ladder["id"], "company": ladder["company"], "title": ladder["title"], "period": ladder["period"]}
    if not verification or not verification.get("time_of_day_cited"):
        return {**row, "excluded": "report time not cited"}
    report = datetime.fromisoformat(verification["report_time"])
    day = results_day(report)
    priced = price_ladder(ladder, candles, cutoff(report))
    figure = reported_figure(ladder, verification)
    row.update(report_time=verification["report_time"], results_day=day, figure=figure, **priced)
    expected = priced["expected"]
    if figure is None:
        return {**row, "excluded": "no cited figure agrees with the settlements"}
    if expected is None:
        return {**row, "excluded": "expected figure not computable"}
    if priced["traded_10_days"] <= 0:
        return {**row, "excluded": "no threshold traded in the 10 days before the report"}
    row.update(surprise(figure, expected))
    if verification.get("matches_contract") is False:
        published = surprise(verification["figure_value"], expected)["outcome"]
        row["mismatch"] = verification.get("mismatch")
        if published != row["outcome"]:
            return {**row, "excluded": "definition differs and changes the beat or miss"}
    reason = universe(prices["tickers"].get(ladder["company"]), report, day)
    return {**row, "excluded": f"outside the universe: {reason}" if reason else None}


def assemble(ladders, verified, candles, prices):
    """Every ladder checked, and 1 event per company and results day: its most-traded ladder that is not excluded
    (addendum 2), with the share's returns net of SPY."""
    rows = [check_ladder(x, verified.get(x["id"]), candles, prices) for x in ladders]
    groups = {}
    for row in rows:
        if row.get("results_day"):
            groups.setdefault((row["company"], row["results_day"]), []).append(row)
    spy = prices["tickers"]["SPY"]["bars"]
    events = []
    for (company, day), group in sorted(groups.items()):
        eligible = [r for r in group if r["excluded"] is None]
        if not eligible:
            continue
        chosen = max(eligible, key=lambda r: r["traded_30_days"])
        bars = prices["tickers"][company]["bars"]
        events.append(
            {
                "event": f"{company} {day}",
                "company": company,
                "results_day": day,
                "report_time": chosen["report_time"],
                "ladder": chosen["ladder"],
                "title": chosen["title"],
                "expected": chosen["expected"],
                "figure": chosen["figure"],
                "outcome": chosen["outcome"],
                "standardised": chosen["standardised"],
                "returns": market_returns(bars, spy, day),
                "other_ladders": sorted(r["ladder"] for r in group if r is not chosen),
            }
        )
    return {"ladders": rows, "events": events}
