"""The plan's tests on known numbers: the beat-minus-miss gap and its interval, accuracy, direction, spread against
move size, and the stopping rules."""

import unittest

from mef.study import accuracy, bootstrap_difference, direction, spearman, study


def event(day, outcome, ret, spread=1.0, median=10.0, standardised=None, drift=None):
    return {
        "results_day": day,
        "outcome": outcome,
        "standardised": standardised,
        "expected": {"median": median, "q25": median - spread / 2, "q75": median + spread / 2, "spread": spread},
        "returns": {"results_day": ret, "two_sessions": ret, "drift_20": drift, "drift_60": None},
    }


def many(n, gap):
    """n events on n dates, alternating beats and misses, beats gap/2 above zero and misses gap/2 below, with noise."""
    rows = []
    for i in range(n):
        noise = ((i * 37) % 11 - 5) / 100
        beat = i % 2 == 0
        rows.append(
            event(
                f"2026-{1 + i // 28:02d}-{1 + i % 28:02d}",
                "beat" if beat else "miss",
                (gap / 2 if beat else -gap / 2) + noise,
            )
        )
    return rows


class BootstrapTests(unittest.TestCase):
    def test_the_gap_between_beats_and_misses_with_its_interval(self):
        result = bootstrap_difference(many(120, 0.10), "results_day", resamples=2000)
        self.assertEqual((result["n"], result["beats"], result["misses"]), (120, 60, 60))
        self.assertAlmostEqual(result["difference"], 0.10, places=2)
        self.assertLess(result["low"], result["difference"])
        self.assertGreater(result["high"], result["difference"])
        self.assertGreater(result["low"], 0)  # a 10-point gap with this noise is detectable
        self.assertAlmostEqual(result["detectable"], 2.8 * result["se"])

    def test_events_on_1_date_are_resampled_together(self):
        # 2 dates, each with 1 beat at +1 and 1 miss at -1: any resample keeps beats and misses paired
        rows = [
            event("2026-01-05", "beat", 0.01),
            event("2026-01-05", "miss", -0.01),
            event("2026-01-06", "beat", 0.01),
            event("2026-01-06", "miss", -0.01),
        ]
        result = bootstrap_difference(rows, "results_day", resamples=500)
        self.assertAlmostEqual(result["low"], 0.02)
        self.assertAlmostEqual(result["high"], 0.02)

    def test_the_same_seed_gives_the_same_interval(self):
        a = bootstrap_difference(many(40, 0.02), "results_day", resamples=500)
        b = bootstrap_difference(many(40, 0.02), "results_day", resamples=500)
        self.assertEqual((a["low"], a["high"]), (b["low"], b["high"]))

    def test_ties_and_missing_returns_are_left_out(self):
        rows = [
            event("2026-01-05", "beat", 0.02),
            event("2026-01-06", None, 0.5),
            event("2026-01-07", "miss", None),
            event("2026-01-08", "miss", -0.02),
        ]
        self.assertEqual(bootstrap_difference(rows, "results_day", resamples=200)["n"], 2)


class SecondaryTests(unittest.TestCase):
    def test_accuracy_is_the_gap_as_a_share_of_the_figure_and_the_share_inside_the_spread(self):
        rows = [
            {"excluded": None, "figure": 11.0, "expected": {"median": 10.0, "q25": 9.0, "q75": 12.0}},
            {"excluded": None, "figure": 8.0, "expected": {"median": 10.0, "q25": 9.0, "q75": 12.0}},
            {"excluded": None, "figure": 10.0, "expected": {"median": 10.0, "q25": None, "q75": None}},
            {"excluded": "outside the universe: below $20m a day", "figure": 1.0, "expected": {"median": 9.0}},
        ]
        a = accuracy(rows)
        self.assertEqual(a["n"], 3)
        self.assertAlmostEqual(a["median_gap_share"], 1 / 11)  # gaps 1/11, 2/8 and 0
        self.assertEqual((a["inside_spread"], a["with_spread"]), (1, 2))

    def test_direction_counts_moves_that_agree_with_the_surprise(self):
        rows = [
            event("d1", "beat", 0.02),
            event("d2", "beat", -0.01),
            event("d3", "miss", -0.03),
            event("d4", "miss", 0.0),
        ]
        self.assertEqual(direction(rows), {"beats": 2, "beats_up": 1, "misses": 2, "misses_down": 1})

    def test_spearman_ranks(self):
        self.assertAlmostEqual(spearman([1, 2, 3, 4], [10, 20, 30, 40]), 1.0)
        self.assertAlmostEqual(spearman([1, 2, 3, 4], [40, 30, 20, 10]), -1.0)
        self.assertAlmostEqual(spearman([1, 2, 3], [5, 5, 6]), 0.8660254, places=6)  # ties share their rank
        self.assertIsNone(spearman([1, 1, 1], [5, 6, 7]))  # a constant input has no rank correlation


class StoppingTests(unittest.TestCase):
    def test_fewer_than_100_events_report_accuracy_only(self):
        result = study(many(60, 0.10), [], resamples=200)
        self.assertEqual(result["conclusion"], "fewer than 100 events: accuracy only")
        self.assertNotIn("primary", result)

    def test_an_interval_including_0_reports_no_measurable_difference(self):
        result = study(many(120, 0.0), [], resamples=500)
        self.assertEqual(result["conclusion"], "no measurable difference")
        self.assertIn("detectable", result["primary"])

    def test_a_clear_gap_is_reported_as_measured(self):
        self.assertEqual(study(many(120, 0.10), [], resamples=500)["conclusion"], "measured difference")


if __name__ == "__main__":
    unittest.main()
