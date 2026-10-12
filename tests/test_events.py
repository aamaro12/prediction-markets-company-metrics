"""Events: results day from the report's time, the price cutoff before it, and returns net of SPY."""

from datetime import datetime, timezone
import unittest

from mef.events import cutoff, market_returns, results_day
from mef.sessions import offset


class TimingTests(unittest.TestCase):
    def test_results_day_follows_the_reports_time_in_new_york(self):
        cases = {
            "2026-08-11T07:00:00-04:00": "2026-08-11",  # before the open: that day
            "2026-08-11T12:30:00-04:00": "2026-08-11",  # during the session: that day (addendum 1)
            "2026-08-11T16:00:00-04:00": "2026-08-12",  # at the close: the next session
            "2026-08-11T20:05:00+00:00": "2026-08-12",  # 16:05 in New York, given in UTC
            "2026-08-15T08:00:00-04:00": "2026-08-17",  # a Saturday: the next session
            "2025-07-03T16:30:00-04:00": "2025-07-07",  # Independence Day falls on the Friday
        }
        for when, day in cases.items():
            with self.subTest(when=when):
                self.assertEqual(results_day(datetime.fromisoformat(when)), day)

    def test_prices_are_read_at_midnight_in_new_york_before_the_reports_date(self):
        report = datetime.fromisoformat("2026-08-11T16:05:00-04:00")
        self.assertEqual(cutoff(report), int(datetime(2026, 8, 11, 4, tzinfo=timezone.utc).timestamp()))
        winter = datetime.fromisoformat("2026-02-05T07:00:00-05:00")
        self.assertEqual(cutoff(winter), int(datetime(2026, 2, 5, 5, tzinfo=timezone.utc).timestamp()))


class ReturnTests(unittest.TestCase):
    def test_returns_are_the_shares_minus_spys_over_the_same_sessions(self):
        day = "2026-08-12"
        before, after, later = offset(day, -1), offset(day, 1), offset(day, 20)
        share = {before: {"close": 100.0}, day: {"close": 110.0}, after: {"close": 99.0}, later: {"close": 121.0}}
        spy = {before: {"close": 500.0}, day: {"close": 505.0}, after: {"close": 500.0}, later: {"close": 550.0}}
        r = market_returns(share, spy, day)
        self.assertAlmostEqual(r["results_day"], 0.10 - 0.01)
        self.assertAlmostEqual(r["two_sessions"], -0.01 - 0.0)
        self.assertAlmostEqual(r["drift_20"], 0.10 - (550 / 505 - 1))
        self.assertIsNone(r["drift_60"])  # no close 60 sessions later
        self.assertIsNone(market_returns({day: {"close": 110.0}}, spy, day)["results_day"])  # no close before


class AssemblyTests(unittest.TestCase):
    """1 company reports 2 figures on 1 day; each exclusion the plan lists removes a ladder or an event."""

    REPORT = "2026-08-11T16:05:00-04:00"
    DAY = "2026-08-12"

    def setUp(self):
        from mef.events import cutoff as cut

        self.at = cut(datetime.fromisoformat(self.REPORT))
        days = [offset(self.DAY, n) for n in range(-25, 2)]
        bars = {d: {"close": 100.0, "volume": 1_000_000} for d in days}
        bars[self.DAY] = {"close": 108.0, "volume": 1_000_000}
        spy = {d: {"close": 500.0, "volume": 1} for d in days}
        self.prices = {
            "tickers": {
                "CAVA": {"outside_universe": None, "reference": {"list_date": "2021-06-15"}, "bars": bars},
                "SPY": {"bars": spy},
            }
        }
        self.ladders = [self.ladder("A", 9.0), self.ladder("B", 95.0, strikes=(90, 100))]
        self.candles = {}
        self.quote("A", (3, 90), (5, 70), (7, 30), (9, 10), volume=50)  # median 6.0, spread 3.0
        self.quote("B", (90, 60), (100, 40), volume=10)
        self.verified = {x["id"]: self.verification(x["id"]) for x in self.ladders}

    def ladder(self, name, figure, strikes=(3, 5, 7, 9)):
        rungs = [
            {"ticker": f"{name}-{s}", "strike": s, "comparison": "greater", "result": "yes" if figure > s else "no"}
            for s in strikes
        ]
        return {
            "id": name,
            "company": "CAVA",
            "title": name,
            "period": "Q2 2026",
            "figure": figure,
            "consistent": True,
            "rungs": rungs,
        }

    def quote(self, name, *points, volume):
        for strike, price in points:
            self.candles[f"{name}-{strike}"] = [
                {"end": self.at - 86400, "bid": price - 1, "ask": price + 1, "last": price, "volume": volume}
            ]

    def verification(self, ladder, **changes):
        return {
            "ladder": ladder,
            "report_time": self.REPORT,
            "time_of_day_cited": True,
            "matches_contract": True,
            "figure_value": None,
            **changes,
        }

    def run_it(self):
        from mef.events import assemble

        return assemble(self.ladders, self.verified, self.candles, self.prices)

    def test_the_event_takes_the_most_traded_ladder_and_its_returns(self):
        result = self.run_it()
        (event,) = result["events"]
        self.assertEqual((event["ladder"], event["results_day"], event["outcome"]), ("A", self.DAY, "beat"))
        self.assertAlmostEqual(event["returns"]["results_day"], 0.08)
        self.assertEqual(event["other_ladders"], ["B"])
        self.assertEqual({row["ladder"] for row in result["ladders"]}, {"A", "B"})  # both serve accuracy

    def test_an_excluded_most_traded_ladder_gives_way_to_the_next(self):  # addendum 2
        self.quote("A", (3, 95), (5, 90), (7, 80), (9, 70), volume=50)  # every threshold above 50%: no median
        result = self.run_it()
        (event,) = result["events"]
        self.assertEqual(event["ladder"], "B")
        reasons = {row["ladder"]: row["excluded"] for row in result["ladders"]}
        self.assertEqual(reasons["A"], "expected figure not computable")
        self.candles["A-9"] = []  # 1 unpriced threshold leaves the rest to bracket 50%: A computes again
        self.quote("A", (3, 90), (5, 70), (7, 30), volume=50)
        self.assertEqual(self.run_it()["events"][0]["ladder"], "A")

    def test_each_exclusion_in_the_plan(self):
        def reasons(**edit):
            self.setUp()
            edit.get("change", lambda: None)()
            result = self.run_it()
            return {row["ladder"]: row["excluded"] for row in result["ladders"]}

        self.assertEqual(reasons(change=lambda: self.verified.pop("A"))["A"], "report time not cited")
        no_time = lambda: self.verified.update(A=self.verification("A", time_of_day_cited=False))  # noqa: E731
        self.assertEqual(reasons(change=no_time)["A"], "report time not cited")
        stale = lambda: [c.update(end=self.at - 11 * 86400) for k, v in self.candles.items() for c in v]  # noqa: E731
        self.assertEqual(reasons(change=stale)["A"], "no threshold traded in the 10 days before the report")
        fund = lambda: self.prices["tickers"]["CAVA"].update(outside_universe="not a common stock (ETF)")  # noqa: E731
        self.assertEqual(reasons(change=fund)["A"], "outside the universe: not a common stock (ETF)")
        later = lambda: self.prices["tickers"]["CAVA"]["reference"].update(list_date="2026-09-01")  # noqa: E731
        self.assertEqual(reasons(change=later)["A"], "outside the universe: listed after the report")

        def thin():
            for row in self.prices["tickers"]["CAVA"]["bars"].values():
                row["volume"] = 1000

        self.assertEqual(reasons(change=thin)["A"], "outside the universe: below $20m a day")
        # Codex finds the company published 5.5 on another definition: a miss where the settled 9.0 is a beat
        flips = lambda: self.verified.update(  # noqa: E731
            A=self.verification("A", matches_contract=False, mismatch="another segment", figure_value=5.5)
        )
        self.assertEqual(reasons(change=flips)["A"], "definition differs and changes the beat or miss")
        same = lambda: self.verified.update(  # noqa: E731
            A=self.verification("A", matches_contract=False, mismatch="rounded", figure_value=8.9)
        )
        self.assertIsNone(reasons(change=same)["A"])
        bound = lambda: self.ladders[0].update(figure=None)  # noqa: E731
        self.assertEqual(reasons(change=bound)["A"], "no cited figure agrees with the settlements")


if __name__ == "__main__":
    unittest.main()
