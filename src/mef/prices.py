"""Share prices and each company's identity, from Massive: split-adjusted daily closes and the ticker reference.

The universe is US common stocks listed on NYSE, Nasdaq or NYSE American. Identity comes from the ticker reference;
the liquidity screen, at least $20m traded a day over the 20 sessions before a report, from the closes themselves.
"""

from datetime import datetime, timezone
import json
import os
from pathlib import Path
from urllib.parse import quote, urlencode

from .fetching import save_json
from .massive import MassiveFetcher

MASSIVE = "https://api.massive.com"
FIRST_DAY = "2024-08-01"  # 20 sessions before the window opens, with room for holidays
MIN_DOLLAR_VOLUME = 20_000_000


def credentials(env_file=None):
    """The Massive key from the environment or a file of KEY=value lines; never printed or saved."""
    key = os.environ.get("MASSIVE_API_KEY")
    if not key and env_file:
        for line in Path(env_file).read_text().splitlines():
            name, sep, value = line.strip().removeprefix("export ").partition("=")
            if sep and name == "MASSIVE_API_KEY":
                key = value.strip().strip("\"'")
    if not key:
        raise ValueError("Share prices need MASSIVE_API_KEY, from the environment or --env-file")
    return key


def identity(details):
    """Why a stock falls outside the universe, from its ticker reference, or None when it is inside."""
    r = (details or {}).get("results") or {}
    if not r:
        return "no ticker reference"
    if r.get("type") != "CS":
        return f"not a common stock ({r.get('type')})"
    if r.get("locale") != "us" or str(r.get("currency_name", "")).lower() != "usd":
        return "not quoted in US dollars on the US market"
    if r.get("primary_exchange") not in {"XNYS", "XNAS", "XASE"}:
        return f"not listed on NYSE, Nasdaq or NYSE American ({r.get('primary_exchange')})"
    return None


def bars(body, ticker):
    """Split-adjusted daily closes and volumes, keyed by session date."""
    if (body or {}).get("ticker") != ticker:
        return {}
    rows = {}
    for r in body.get("results") or []:
        if r.get("t") is None or not r.get("c") or r["c"] <= 0:
            continue
        day = datetime.fromtimestamp(r["t"] / 1000, timezone.utc).date().isoformat()
        rows[day] = {"close": r["c"], "volume": r.get("v") or 0}
    return rows


def collect(tickers, output, env_file=None, user_agent=None, last_day=None):
    """Identity and daily closes for each company, and SPY's closes, saved to prices.json."""
    fetcher = MassiveFetcher(
        Path(output) / "massive",
        user_agent,
        credentials(env_file),
        max_requests=10 * len(tickers) + 10,
        min_interval=13,
    )
    last_day = last_day or datetime.now(timezone.utc).date().isoformat()
    params = urlencode({"adjusted": "true", "sort": "asc", "limit": 50000})
    found = {}
    for ticker in ["SPY", *sorted(set(tickers))]:
        entry = {}
        if ticker != "SPY":
            rec = fetcher.fetch(f"{MASSIVE}/v3/reference/tickers/{quote(ticker)}", "massive_reference")
            details = json.loads(fetcher.text(rec)) if rec["status"] == "ok" else None
            result = (details or {}).get("results") or {}
            entry["reference"] = {k: result.get(k) for k in ("name", "type", "primary_exchange", "list_date", "active")}
            entry["outside_universe"] = identity(details)
        rec = fetcher.fetch(
            f"{MASSIVE}/v2/aggs/ticker/{quote(ticker)}/range/1/day/{FIRST_DAY}/{last_day}?{params}",
            "massive_daily_prices",
        )
        entry["bars"] = bars(json.loads(fetcher.text(rec)), ticker) if rec["status"] == "ok" else {}
        entry["status"] = rec["status"]
        found[ticker] = entry
    save_json(Path(output) / "prices.json", {"first_day": FIRST_DAY, "last_day": last_day, "tickers": found})
    return {
        "tickers": len(found),
        "with_bars": sum(bool(e["bars"]) for e in found.values()),
        "requests": fetcher.requests,
    }
