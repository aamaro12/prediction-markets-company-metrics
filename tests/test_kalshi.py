"""Kalshi's company-figure ladders: which series count, how rungs group into ladders, and how a rung is priced."""

from datetime import datetime, timezone
import unittest

from mef.kalshi import (
    close_before,
    company_of,
    kept_series,
    ladders_from_markets,
    normalise_candles,
    parse_figure,
    threshold_of,
)

UTC = timezone.utc


def rung(event, strike, result, close="2026-08-11T20:52:46Z", figure="9", strike_type="greater", **extra):
    return {
        "ticker": f"{event}-{strike}",
        "event_ticker": event,
        "strike_type": strike_type,
        "floor_strike": strike,
        "status": "finalized",
        "result": result,
        "expiration_value": figure,
        "close_time": close,
        "rules_primary": f"If CAVA reports above {strike}% same restaurant sales growth in Q2 2026, the market resolves to Yes.",
        **extra,
    }


class SeriesTests(unittest.TestCase):
    def test_a_series_is_named_after_its_stock_except_the_listed_exceptions(self):
        self.assertEqual(company_of("KXCAVA"), "CAVA")
        self.assertEqual(company_of("KXBOEING"), "BA")
        self.assertEqual(company_of("TESLAPROD"), "TSLA")  # an older product without the KX prefix

    def test_only_series_whose_terms_settle_on_a_reported_figure_count(self):
        catalogue = [
            {"ticker": "KXCAVA", "contract_terms_url": "https://kalshi.com/terms/QUARTERKPI.pdf"},
            {"ticker": "KXCAVAA", "contract_terms_url": "https://kalshi.com/terms/ANNUALKPI.pdf"},
            {"ticker": "KXTESLA", "contract_terms_url": "https://kalshi.com/terms/TESLA.pdf"},
            {"ticker": "KXGOOGSHARE", "contract_terms_url": "https://kalshi.com/terms/GOOGLESHARE.pdf"},
        ]
        self.assertEqual([s["ticker"] for s in kept_series(catalogue)], ["KXCAVA", "KXTESLA"])


class FigureTests(unittest.TestCase):
    def test_a_settled_figure_is_read_from_the_venues_text(self):
        for text, value in (("358,023", 358023), ("9", 9), ("4.4%", 4.4), ("$10.5", 10.5), ("-2.6", -2.6)):
            with self.subTest(text=text):
                self.assertEqual(parse_figure(text), value)
        for text, value in (("2.02e+11", 2.02e11), ("18.91 million", 18_910_000), ("$1.2 billion", 1.2e9)):
            with self.subTest(text=text):
                self.assertAlmostEqual(parse_figure(text), value)
        for text in ("", None, "n/a", "above 3.6 billion", "at least 4%"):  # a bound is not the figure
            self.assertIsNone(parse_figure(text))

    def test_a_threshold_comes_from_the_strike_or_from_the_words_of_older_products(self):
        self.assertEqual(
            threshold_of(
                {
                    "floor_strike": 195e9,
                    "strike_type": "structured",
                    "rules_primary": "If Coinbase reports Above 195000000000 total trading volume",
                }
            ),
            (195e9, "greater"),
        )
        older = {
            "subtitle": "8 million",
            "yes_sub_title": "Above 8 million",
            "strike_type": None,
            "rules_primary": "If Netflix adds 8 million subscribers or more in 2024 Q4, then the market resolves to Yes.",
        }
        self.assertEqual(threshold_of(older), (8_000_000, "greater_or_equal"))
        self.assertIsNone(threshold_of({"strike_type": "between", "floor_strike": 3, "rules_primary": ""}))


class LadderTests(unittest.TestCase):
    START = datetime(2024, 10, 12, tzinfo=UTC)
    END = datetime(2026, 10, 12, tzinfo=UTC)

    def test_rungs_group_into_1_ladder_per_event_in_strike_order(self):
        markets = [
            rung("KXCAVA-26AUGCOMP", 8, "yes"),
            rung("KXCAVA-26AUGCOMP", 3, "yes"),
            rung("KXCAVA-26AUGCOMP", 10, "no"),
        ]
        (ladder,) = ladders_from_markets(
            markets, {"KXCAVA-26AUGCOMP": {"title": "CAVA comps in Q2"}}, "KXCAVA", self.START, self.END
        )
        self.assertEqual(ladder["id"], "KXCAVA-26AUGCOMP")
        self.assertEqual(ladder["company"], "CAVA")
        self.assertEqual([r["strike"] for r in ladder["rungs"]], [3, 8, 10])
        self.assertEqual(ladder["figure"], 9)
        self.assertEqual(ladder["closed_at"], "2026-08-11T20:52:46+00:00")
        self.assertEqual(ladder["period"], "Q2 2026")

    def test_a_ladder_needs_settled_binary_rungs_on_above_thresholds_inside_the_window(self):
        def one(markets):
            return ladders_from_markets(markets, {}, "KXCAVA", self.START, self.END)

        self.assertEqual(one([rung("E1", 3, "yes"), rung("E1", 8, "")]), [])  # an open rung: not resolved
        self.assertEqual(one([rung("E2", 3, "yes"), rung("E2", 8, "scalar")]), [])  # a scalar settlement
        self.assertEqual(one([rung("E3", 3, "yes", strike_type="between")]), [])  # not an "above" threshold
        self.assertEqual(one([rung("E4", 3, "yes", close="2024-09-30T20:00:00Z")]), [])  # before the price window
        self.assertEqual(len(one([rung("E6", 3, "yes")])), 1)

    def test_a_figure_stated_only_as_a_bound_leaves_the_ladder_for_codex_to_cite(self):
        (ladder,) = ladders_from_markets([rung("E5", 3, "yes", figure="above 3")], {}, "KXCAVA", self.START, self.END)
        self.assertIsNone(ladder["figure"])
        self.assertEqual(ladder["figure_text"], "above 3")

    def test_a_figure_must_agree_with_every_thresholds_settlement(self):
        def consistent(figure, *rungs):
            (ladder,) = ladders_from_markets(list(rungs), {}, "KXCAVA", self.START, self.END)
            return ladder["consistent"]

        self.assertTrue(consistent(9, rung("E7", 8, "yes", figure="9"), rung("E7", 10, "no", figure="9")))
        self.assertFalse(consistent(9, rung("E8", 8, "no", figure="9"), rung("E8", 10, "no", figure="9")))
        at = rung("E9", 9, "yes", figure="9", strike_type="greater_or_equal")  # 9 or more includes 9
        self.assertTrue(consistent(9, at))
        self.assertFalse(consistent(9, rung("E10", 9, "yes", figure="9")))  # above 9 excludes 9

    def test_a_figure_stated_in_other_units_than_the_thresholds_is_converted_to_theirs(self):
        # Netflix's thresholds count millions while its figure reads "5.1 million"; Altria's count units while its
        # figure reads "15,554" million
        netflix = [rung("N", s, "no", figure="5.1 million") for s in (6, 7, 8)]
        (ladder,) = ladders_from_markets(netflix, {}, "NETFLIXSUBS", self.START, self.END)
        self.assertEqual((ladder["figure"], ladder["consistent"], ladder["figure_scale"]), (5.1, True, 1e-6))
        altria = [rung("M", s * 1e9, r, figure="15,554") for s, r in ((14.5, "yes"), (15.5, "yes"), (16, "no"))]
        (ladder,) = ladders_from_markets(altria, {}, "KXMO", self.START, self.END)
        self.assertEqual((ladder["figure"], ladder["consistent"]), (15_554_000_000, True))
        wrong = [rung("W", 8, "no", figure="9"), rung("W", 10, "no", figure="9")]  # no scale makes 9 agree
        (ladder,) = ladders_from_markets(wrong, {}, "KXCAVA", self.START, self.END)
        self.assertEqual((ladder["figure"], ladder["consistent"]), (9, False))


class CandleTests(unittest.TestCase):
    def test_both_partitions_name_their_fields_differently_and_read_alike(self):
        live = {
            "candlesticks": [
                {
                    "end_period_ts": 100,
                    "volume_fp": "12",
                    "price": {"close_dollars": "0.73"},
                    "yes_bid": {"close_dollars": "0.72"},
                    "yes_ask": {"close_dollars": "0.74"},
                }
            ]
        }
        archived = {
            "candlesticks": [
                {
                    "end_period_ts": 100,
                    "volume": "12",
                    "price": {"close": "0.73"},
                    "yes_bid": {"close": "0.72"},
                    "yes_ask": {"close": "0.74"},
                }
            ]
        }
        self.assertEqual(normalise_candles(live), normalise_candles(archived))
        self.assertEqual(
            normalise_candles(live)[0], {"end": 100, "bid": 72.0, "ask": 74.0, "last": 73.0, "volume": 12.0}
        )

    def test_a_rung_is_priced_at_the_last_close_before_the_cutoff(self):
        day = 86400
        candles = [
            {"end": 10 * day, "bid": 40.0, "ask": 44.0, "last": 41.0, "volume": 5.0},
            {"end": 12 * day, "bid": 0.0, "ask": 50.0, "last": 47.0, "volume": 3.0},  # no bid: the last trade
            {"end": 13 * day, "bid": 60.0, "ask": 62.0, "last": 61.0, "volume": 9.0},  # after the cutoff
        ]
        priced = close_before(candles, cutoff=12 * day)
        self.assertEqual((priced["price"], priced["basis"]), (47.0, "last_trade"))
        self.assertEqual(close_before(candles, cutoff=11 * day)["price"], 42.0)  # the mid of a two-sided close
        self.assertEqual(close_before(candles, cutoff=11 * day)["basis"], "mid")
        self.assertEqual(close_before(candles, cutoff=12 * day)["traded_10_days"], 8.0)
        self.assertEqual(close_before(candles, cutoff=12 * day)["traded_30_days"], 8.0)
        self.assertIsNone(close_before(candles, cutoff=9 * day))  # nothing before the cutoff
        self.assertEqual(close_before(candles, cutoff=25 * day)["traded_10_days"], 0.0)  # nothing from day 15 to 25


if __name__ == "__main__":
    unittest.main()
