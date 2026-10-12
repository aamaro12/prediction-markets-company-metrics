"""Command line: each step reads the files of the step before and writes its own to runs/."""

import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
import sys

from . import __version__
from .fetching import Fetcher, resolve_user_agent, save_json

WINDOW = (datetime(2024, 10, 12, tzinfo=timezone.utc), datetime(2026, 10, 12, tzinfo=timezone.utc))  # the plan's


def ladders(args):
    from .kalshi import KALSHI, get_json, kept_series, series_ladders

    out = Path(args.output)
    fetcher = Fetcher(out / "kalshi", resolve_user_agent(args.user_agent), max_requests=2000, min_interval=0.35)
    body, record = get_json(fetcher, f"{KALSHI}/series", "kalshi_series_catalogue")
    if body is None:
        raise ValueError(f"Kalshi's series catalogue was not read: {record['status']}")
    series = kept_series(body.get("series") or [])
    found, coverage = [], []
    for s in series:
        rows, status = series_ladders(fetcher, s, *WINDOW)
        found += rows
        coverage.append(status)
    result = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "window": [w.isoformat() for w in WINDOW],
        "series": len(series),
        "requests": fetcher.requests,
        "coverage": coverage,
        "ladders": found,
    }
    save_json(out / "ladders.json", result)
    return {"ladders": len(found), "companies": len({x["company"] for x in found}), "requests": fetcher.requests}


def read(args):
    from .read import read_sources

    return read_sources(args.urls, args.sources, args.find, args.replay, args.user_agent)


def verify(args):
    """Check Codex's verifications: each must cite the report's date and the published figure, or say why it cannot."""
    from .read import check_verification

    checked, unverifiable, failed = [], [], []
    for path in args.verifications:
        for v in json.loads(Path(path).read_text()).get("verifications", []):
            if v.get("unverifiable"):
                unverifiable.append({"ladder": v.get("ladder"), "reason": v["unverifiable"], "file": path})
                continue
            try:
                checked.append(check_verification(v, args.sources, args.replay))
            except (ValueError, KeyError, TypeError) as error:
                failed.append({"ladder": v.get("ladder"), "error": str(error), "file": path})
    if args.output:
        save_json(Path(args.output), {"verified": checked, "unverifiable": unverifiable, "failed": failed})
    return {"verified": len(checked), "unverifiable": len(unverifiable), "failed": failed}


def comparatives(args):
    """Check Codex's earlier figures: each must be cited from the company's publications, or say why it cannot."""
    from .benchmark import check_comparative

    checked, unverifiable, failed = [], [], []
    for path in args.comparatives:
        for c in json.loads(Path(path).read_text()).get("comparatives", []):
            if c.get("unverifiable"):
                unverifiable.append({"ladder": c.get("ladder"), "reason": c["unverifiable"], "file": path})
                continue
            try:
                checked.append(check_comparative(c, args.sources, args.replay))
            except (ValueError, KeyError, TypeError) as error:
                failed.append({"ladder": c.get("ladder"), "error": str(error), "file": path})
    if args.output:
        save_json(Path(args.output), {"checked": checked, "unverifiable": unverifiable, "failed": failed})
    return {"checked": len(checked), "unverifiable": len(unverifiable), "failed": failed}


def explanations(args):
    """Check Codex's explanations of the plan's 10 largest moves against the surprise, each cited from news published by
    the end of results day."""
    from .explain import against_surprise, check_explanation

    chosen = {e["ladder"]: e for e in against_surprise(json.loads(Path(args.events).read_text())["events"])}
    checked, unexplained, failed = [], [], []
    for path in args.explanations:
        for x in json.loads(Path(path).read_text()).get("explanations", []):
            if x.get("ladder") not in chosen:
                failed.append({"ladder": x.get("ladder"), "error": "not among the 10 largest moves", "file": path})
                continue
            if x.get("unexplained"):
                unexplained.append({"ladder": x["ladder"], "reason": x["unexplained"], "file": path})
                continue
            try:
                checked.append(check_explanation(x, chosen[x["ladder"]], args.sources, args.replay))
            except (ValueError, KeyError, TypeError) as error:
                failed.append({"ladder": x.get("ladder"), "error": str(error), "file": path})
    missing = sorted(set(chosen) - {x["ladder"] for x in checked + unexplained})
    if args.output:
        save_json(Path(args.output), {"explained": checked, "unexplained": unexplained, "failed": failed})
    return {"explained": len(checked), "unexplained": len(unexplained), "failed": failed, "missing": missing}


def candles(args):
    """Each threshold's daily candles from 45 days before its ladder closed to 2 days after, so the last close before
    any verified report date can be chosen later without fetching again."""
    from .kalshi import candles as fetch, when

    data = json.loads(Path(args.ladders).read_text())
    fetcher = Fetcher(
        Path(args.output) / "kalshi", resolve_user_agent(args.user_agent), max_requests=5000, min_interval=0.35
    )
    found, failed = {}, 0
    for ladder in data["ladders"]:
        end = int(when(ladder["closed_at"]).timestamp()) + 2 * 86400
        for rung in ladder["rungs"]:
            rows, status = fetch(fetcher, ladder, rung, end, days=47)
            found[rung["ticker"]] = {"status": status, "candles": rows}
            failed += status != "ok"
    save_json(
        Path(args.output) / "candles.json", {"generated_at": datetime.now(timezone.utc).isoformat(), "rungs": found}
    )
    return {"rungs": len(found), "failed": failed, "requests": fetcher.requests}


def prices(args):
    from .prices import collect

    data = json.loads(Path(args.ladders).read_text())
    agent = resolve_user_agent(args.user_agent)
    return collect([x["company"] for x in data["ladders"]], args.output, args.env_file, agent)


def estimate_check(args):
    from .estimates import check_estimate

    ladders = json.loads(Path(args.open).read_text())["ladders"]
    checked = [check_estimate(json.loads(Path(f).read_text()), ladders, args.sources) for f in args.estimates]
    return {"passed": [c["ladder"] for c in checked]}


def events(args):
    """The dataset: every ladder checked and 1 event per company and results day, with a hash to freeze it by."""
    import hashlib

    from .events import assemble

    ladders = json.loads(Path(args.ladders).read_text())["ladders"]
    verified = {}
    for path in args.verified:
        for v in json.loads(Path(path).read_text())["verified"]:
            verified[v["ladder"]] = v
    candles = {k: v["candles"] for k, v in json.loads(Path(args.candles).read_text())["rungs"].items()}
    result = assemble(ladders, verified, candles, json.loads(Path(args.prices).read_text()))
    save_json(Path(args.output), result)
    reasons = {}
    for row in result["ladders"]:
        reasons[row["excluded"] or "kept"] = reasons.get(row["excluded"] or "kept", 0) + 1
    return {
        "ladders": len(ladders),
        "by_reason": reasons,
        "events": len(result["events"]),
        "sha256": hashlib.sha256(Path(args.output).read_bytes()).hexdigest(),
    }


def run_study(args):
    from .study import study

    data = json.loads(Path(args.events).read_text())
    result = study(data["events"], data["ladders"])
    save_json(Path(args.output), result)
    return result


def run_benchmark(args):
    """The market's expected figure against 2 simple forecasts, from the tracked data alone."""
    from .benchmark import benchmark

    rows = json.loads(Path(args.events).read_text())["ladders"]
    earlier = {c["ladder"]: c for c in json.loads(Path(args.comparatives).read_text())["checked"]}
    result = benchmark(rows, earlier)
    save_json(Path(args.output), result)
    return result


def parser():
    p = argparse.ArgumentParser(prog="mef", description="Research prototype, not investment advice.")
    p.add_argument("--version", action="version", version=f"mef {__version__}")
    commands = p.add_subparsers(dest="command", required=True)
    c = commands.add_parser("ladders", help="Every resolved company-figure ladder in the plan's window")
    c.add_argument("--output", required=True)
    c.add_argument("--user-agent")
    c.set_defaults(handler=ladders)

    c = commands.add_parser("read", help="Read sources and list the passages a citation can point at")
    c.add_argument("urls", nargs="+")
    c.add_argument("--sources", required=True, help="The folder that keeps every source read")
    c.add_argument("--find", nargs="*", default=[], help="Regular expressions a passage must match")
    c.add_argument("--replay")
    c.add_argument("--user-agent")
    c.set_defaults(handler=read)

    c = commands.add_parser("verify", help="Check Codex's verifications of report times and published figures")
    c.add_argument("verifications", nargs="+", help="JSON files, each with a list under 'verifications'")
    c.add_argument("--sources", required=True)
    c.add_argument("--output", help="Where to write the checked verifications")
    c.add_argument("--replay")
    c.set_defaults(handler=verify)

    c = commands.add_parser("comparatives", help="Check Codex's citations of each figure a year and a quarter earlier")
    c.add_argument("comparatives", nargs="+", help="JSON files, each with a list under 'comparatives'")
    c.add_argument("--sources", required=True)
    c.add_argument("--output", help="Where to write the checked comparatives")
    c.add_argument("--replay")
    c.set_defaults(handler=comparatives)

    c = commands.add_parser(
        "explanations", help="Check Codex's explanations of the 10 largest moves against the surprise"
    )
    c.add_argument("explanations", nargs="+", help="JSON files, each with a list under 'explanations'")
    c.add_argument("--events", required=True)
    c.add_argument("--sources", required=True)
    c.add_argument("--output", help="Where to write the checked explanations")
    c.add_argument("--replay")
    c.set_defaults(handler=explanations)

    c = commands.add_parser("candles", help="Each threshold's daily candles around its ladder's close")
    c.add_argument("--ladders", required=True)
    c.add_argument("--output", required=True)
    c.add_argument("--user-agent")
    c.set_defaults(handler=candles)

    c = commands.add_parser("prices", help="Each company's identity and daily closes, and SPY's, from Massive")
    c.add_argument("--ladders", required=True)
    c.add_argument("--output", required=True)
    c.add_argument("--env-file", help="A file holding MASSIVE_API_KEY; it is read, never printed or saved")
    c.add_argument("--user-agent")
    c.set_defaults(handler=prices)

    c = commands.add_parser("estimate-check", help="Check Codex's estimates for the third-quarter replication")
    c.add_argument("estimates", nargs="+")
    c.add_argument("--open", required=True, help="The open third-quarter ladders")
    c.add_argument("--sources", required=True)
    c.set_defaults(handler=estimate_check)

    c = commands.add_parser("events", help="Assemble the dataset: every ladder checked, 1 event per company and day")
    c.add_argument("--ladders", required=True)
    c.add_argument("--verified", nargs="+", required=True, help="Outputs of mef verify --output")
    c.add_argument("--candles", required=True)
    c.add_argument("--prices", required=True)
    c.add_argument("--output", required=True)
    c.set_defaults(handler=events)

    c = commands.add_parser("study", help="Run the plan's tests once on the frozen dataset")
    c.add_argument("--events", required=True)
    c.add_argument("--output", required=True)
    c.set_defaults(handler=run_study)

    c = commands.add_parser(
        "benchmark", help="The market's expected figure against 2 simple forecasts, outside the plan"
    )
    c.add_argument("--events", required=True)
    c.add_argument("--comparatives", required=True, help="The output of mef comparatives --output")
    c.add_argument("--output", required=True)
    c.set_defaults(handler=run_benchmark)
    return p


def main(argv=None):
    args = parser().parse_args(argv)
    try:
        print(json.dumps(args.handler(args), indent=2))
    except ValueError as error:
        print(f"mef: {error}", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
