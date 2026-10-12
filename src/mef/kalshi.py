"""Kalshi's company-figure ladders: which series settle on a reported figure, their resolved ladders, and each
threshold's daily closes before a report.

A ladder is 1 event, 1 reported figure: contracts "Will <company> report above <X> <figure> in <period>?" at several
thresholds X. Series are kept by the venue's contract terms file: the quarterly KPI products and the older single-company
products on 1 reported figure.
"""

from datetime import datetime, timezone
import json
import math
import re
from urllib.parse import quote, urlencode

KALSHI = "https://external-api.kalshi.com/trade-api/v2"
TERMS = {
    "QUARTERKPI.pdf",
    "QUARTERKPIS.pdf",
    "TESLA.pdf",
    "TESLAPROD.pdf",
    "NFLXSUBS.pdf",
    "SPOTIFYSUBS.pdf",
    "NYTSUBS.pdf",
    "METADAP.pdf",
    "FBDAU.pdf",
    "RHGOLD.pdf",
    "SOFIMEMBERS.pdf",
    "CBVOLUME.pdf",
}
# Series not named after their stock
COMPANY = {
    "TESLA": "TSLA",
    "TESLAPROD": "TSLA",
    "NETFLIXSUBS": "NFLX",
    "SPOTIFYSUBS": "SPOT",
    "NYTSUBS": "NYT",
    "METADAP": "META",
    "FBDAU": "META",
    "RHGOLD": "HOOD",
    "SOFIMEMBERS": "SOFI",
    "CBVOLUME": "COIN",
    "BOEING": "BA",
    "COINBASE": "COIN",
    "DASHORDERS": "DASH",
    "DISNEYSUBS": "DIS",
    "MATCHPAYERS": "MTCH",
    "METAHEADCOUNT": "META",
    "PALANTIR": "PLTR",
    "PLANETFITNESSSUBS": "PLNT",
    "SPOTIFYMAU": "SPOT",
    "UBERTRIPS": "UBER",
    "UBERKPI": "UBER",
    "SNOWFLAKE": "SNOW",
    "TESLASEMI": "TSLA",
    "DKNGMUP": "DKNG",
}
UNITS = {"%": 1, "thousand": 1e3, "million": 1e6, "billion": 1e9, "trillion": 1e12}
BOUND = re.compile(r"\b(?:above|below|over|under|at least|at most|more than|less than|between)\b", re.I)
PERIOD = re.compile(r"\b(Q[1-4])\s+(\d{4})\b|\b(\d{4})\s+(Q[1-4])\b")


def company_of(series):
    """The stock a series reports on: its name after the KX prefix, unless listed in COMPANY."""
    name = series.removeprefix("KX")
    return COMPANY.get(name, name)


def terms(series):
    return (series.get("contract_terms_url") or "").split("/")[-1]


def kept_series(catalogue):
    """The series whose contract terms settle on a figure a company reports."""
    return [s for s in catalogue if terms(s) in TERMS]


def parse_figure(text):
    """A figure as the venue states it, such as '358,023', '4.4%', '2.02e+11' or '18.91 million', as a number in
    absolute units. A bound such as 'above 3.6 billion' is not a figure."""
    text = str(text or "").strip()
    if not text or BOUND.search(text):
        return None
    match = re.fullmatch(r"\$?\s*(-?[\d,]*\.?\d+(?:e[+-]?\d+)?)\s*(%|thousand|million|billion|trillion)?", text, re.I)
    if not match:
        return None
    value = float(match.group(1).replace(",", "")) * UNITS.get((match.group(2) or "%").lower(), 1)
    return int(value) if value.is_integer() and abs(value) < 1e15 else value


def threshold_of(market):
    """A rung's threshold in absolute units and how it compares: (value, "greater" or "greater_or_equal").

    The quarterly products state it as a strike; the older ones only in words, such as 'Above 8 million', with the
    rules saying whether the threshold itself counts ('8 million or more'). None for any other kind of rung."""
    kind = market.get("strike_type")
    rules = market.get("rules_primary") or ""
    if kind in ("greater", "greater_or_equal"):
        comparison = kind
    elif kind in ("structured", None, ""):
        if re.search(r"\bor more\b|\bat least\b", rules, re.I):
            comparison = "greater_or_equal"
        elif re.search(r"\babove\b|\bmore than\b|\bgreater than\b|\bexceeds?\b", rules, re.I):
            comparison = "greater"
        else:
            return None
    else:
        return None
    value = market.get("floor_strike")
    for key in ("yes_sub_title", "subtitle"):
        if value is not None:
            break
        value = parse_figure(re.sub(r"(?i)^\s*(?:above|over|more than|at least)\s+", "", str(market.get(key) or "")))
    return (value, comparison) if value is not None else None


def agrees(figure, value, comparison, result):
    """Whether a figure agrees with 1 threshold's settlement."""
    above = figure >= value if comparison == "greater_or_equal" else figure > value
    return above == (result == "yes")


SCALES = (1, 1e-3, 1e3, 1e-6, 1e6, 1e-9, 1e9)


def in_threshold_units(figure, rungs):
    """The figure in its thresholds' units, and the scale applied: the venue can state a figure in millions against
    thresholds in units, or the reverse. Only a figure more than 30 times larger or smaller than the thresholds is
    converted, so a conversion cannot hide a figure that disagrees with its settlements. Of the scales that agree with
    every settlement, the one nearest the thresholds; the unscaled figure and None when none agrees."""
    middle = abs(rungs[len(rungs) // 2]["strike"]) or 1

    def near(value):
        return value == 0 or 1 / 30 <= abs(value) / middle <= 30

    candidates = [1] if near(figure) else [k for k in SCALES if near(figure * k)]
    agreeing = [
        k for k in candidates if all(agrees(figure * k, r["strike"], r["comparison"], r["result"]) for r in rungs)
    ]
    if not agreeing:
        return figure, None
    best = min(agreeing, key=lambda k: abs(math.log10(abs(figure * k) or 1) - math.log10(middle)))
    value = figure * best
    return (int(round(value)) if abs(value - round(value)) < 1e-6 * max(1, abs(value)) else round(value, 10)), best


def period_of(rules, title=""):
    for text in (rules or "", title or ""):
        match = PERIOD.search(text)
        if match:
            quarter, year = (match.group(1), match.group(2)) if match.group(1) else (match.group(4), match.group(3))
            return f"{quarter} {year}"
    return None


def when(value):
    return datetime.fromisoformat(value.replace("Z", "+00:00")).astimezone(timezone.utc)


def ladders_from_markets(markets, events, series, start, end):
    """Resolved ladders: every rung of 1 event settled Yes or No on an "above X" threshold, closed inside the window.
    A ladder with any open, scalar or other rung is left out. Where the venue states the settled figure only as a
    bound, the figure is None and Codex cites it from the company's release."""
    by_event = {}
    for m in markets:
        by_event.setdefault(m["event_ticker"], []).append(m)
    ladders = []
    for event, rungs in sorted(by_event.items()):
        thresholds = {r["ticker"]: threshold_of(r) for r in rungs}
        if any(r.get("result") not in ("yes", "no") or not thresholds[r["ticker"]] for r in rungs):
            continue
        if any(not r.get("close_time") for r in rungs):
            continue
        closed = min(when(r["close_time"]) for r in rungs)
        if not start <= closed <= end:
            continue
        figures = {parse_figure(r.get("expiration_value")) for r in rungs}
        figure = figures.pop() if len(figures) == 1 else None
        meta = events.get(event) or {}
        rungs = sorted(rungs, key=lambda r: thresholds[r["ticker"]][0])
        ladder_rungs = [
            {
                "ticker": r["ticker"],
                "strike": thresholds[r["ticker"]][0],
                "comparison": thresholds[r["ticker"]][1],
                "result": r["result"],
            }
            for r in rungs
        ]
        scale = None
        if figure is not None:
            figure, scale = in_threshold_units(figure, ladder_rungs)
        ladders.append(
            {
                "id": event,
                "series": series,
                "company": company_of(series),
                "title": meta.get("title") or rungs[0].get("title"),
                "period": period_of(rungs[0].get("rules_primary"), meta.get("title")),
                "closed_at": closed.isoformat(),
                "figure": figure,
                "figure_text": rungs[0].get("expiration_value"),
                "figure_scale": scale,
                "consistent": None if figure is None else scale is not None,
                "rules": rungs[0].get("rules_primary"),
                "partition": rungs[0].get("_partition", "live"),
                "rungs": ladder_rungs,
            }
        )
    return ladders


def cents(block, *keys):
    """A price in dollars, under the live partition's or the archive's field name, in cents."""
    for key in keys:
        value = (block or {}).get(key)
        if value not in (None, ""):
            return round(float(value) * 100, 4)
    return None


def normalise_candles(body):
    """Daily candles in cents, whatever the partition's field names."""
    rows = []
    for c in (body or {}).get("candlesticks") or []:
        volume = c.get("volume_fp", c.get("volume"))
        rows.append(
            {
                "end": int(c["end_period_ts"]),
                "bid": cents(c.get("yes_bid"), "close_dollars", "close"),
                "ask": cents(c.get("yes_ask"), "close_dollars", "close"),
                "last": cents(c.get("price"), "close_dollars", "close"),
                "volume": float(volume) if volume not in (None, "") else 0.0,
            }
        )
    return sorted(rows, key=lambda r: r["end"])


def close_before(candles, cutoff):
    """A rung's price at its last daily close at or before the cutoff: the mid of a two-sided close, else the last
    trade; with the contracts traded in the 10 and 30 days before the cutoff."""
    before = [c for c in candles if c["end"] <= cutoff]
    if not before:
        return None
    last = before[-1]
    two_sided = last["bid"] is not None and last["ask"] is not None and 0 < last["bid"] <= last["ask"] < 100
    price, basis = ((last["bid"] + last["ask"]) / 2, "mid") if two_sided else (last["last"], "last_trade")
    traded = {days: sum(c["volume"] for c in before if c["end"] > cutoff - days * 86400) for days in (10, 30)}
    return {
        "price": price,
        "basis": basis if price is not None else None,
        "close_end": last["end"],
        "traded_10_days": traded[10],
        "traded_30_days": traded[30],
    }


def get_json(fetcher, url, kind):
    record = fetcher.fetch(url, kind)
    if record["status"] != "ok":
        return None, record
    try:
        return json.loads(fetcher.text(record)), record
    except ValueError:
        return None, {**record, "status": "invalid_json"}


def paged(fetcher, url, key, kind, pages=10):
    items, cursor = [], ""
    for _ in range(pages):
        body, record = get_json(fetcher, url + (f"&cursor={quote(cursor)}" if cursor else ""), kind)
        if body is None:
            return items, record["status"]
        items += body.get(key) or []
        cursor = body.get("cursor") or ""
        if not cursor:
            return items, "ok"
    return items, "truncated"


def series_ladders(fetcher, series, start, end):
    """1 series' resolved ladders: /events nests the markets of the live partition, and /historical/markets adds those
    settled before the venue's historical cutoff."""
    ticker = series["ticker"]
    events, status = paged(
        fetcher, f"{KALSHI}/events?series_ticker={ticker}&with_nested_markets=true&limit=200", "events", "kalshi_events"
    )
    meta = {e["event_ticker"]: {"title": e.get("title"), "sub_title": e.get("sub_title")} for e in events}
    markets = {m["ticker"]: {**m, "_partition": "live"} for e in events for m in e.get("markets") or []}
    archived, archive_status = paged(
        fetcher, f"{KALSHI}/historical/markets?series_ticker={ticker}&limit=1000", "markets", "kalshi_archive"
    )
    for m in archived:
        markets.setdefault(m["ticker"], {**m, "_partition": "historical"})
    ladders = ladders_from_markets(list(markets.values()), meta, ticker, start, end)
    return ladders, {"series": ticker, "events": status, "archive": archive_status, "markets": len(markets)}


def candles(fetcher, ladder, rung, end, days=40):
    """A rung's daily candles over the days before `end`, from its partition's endpoint."""
    params = urlencode({"start_ts": end - days * 86400, "end_ts": end, "period_interval": 1440})
    base = (
        f"{KALSHI}/historical/markets/{rung['ticker']}/candlesticks"
        if ladder["partition"] == "historical"
        else f"{KALSHI}/series/{ladder['series']}/markets/{rung['ticker']}/candlesticks"
    )
    body, record = get_json(fetcher, f"{base}?{params}", "kalshi_candles")
    return normalise_candles(body), record["status"]
