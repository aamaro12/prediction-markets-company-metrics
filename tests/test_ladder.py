"""The market's expected figure: a ladder's prices, made to fall as the threshold rises, read as a distribution."""

import unittest

from mef.ladder import expected_figure, falling, quantile, surprise


class DistributionTests(unittest.TestCase):
    def test_prices_that_rise_with_the_threshold_are_pooled_into_a_falling_sequence(self):
        self.assertEqual(falling([90, 60, 65, 10]), [90, 62.5, 62.5, 10])
        self.assertEqual(falling([90, 70, 30, 10]), [90, 70, 30, 10])
        self.assertEqual(falling([20, 40, 60]), [40, 40, 40])

    def test_quantiles_interpolate_between_the_thresholds_that_bracket_them(self):
        points = [(3, 90), (5, 70), (7, 30), (9, 10)]
        self.assertAlmostEqual(quantile(points, 0.5), 6.0)  # 50% lies between 70% at 5 and 30% at 7
        self.assertAlmostEqual(quantile(points, 0.25), 4.5)  # above 4.5 with 75%
        self.assertAlmostEqual(quantile(points, 0.75), 7.5)  # above 7.5 with 25%
        self.assertAlmostEqual(quantile([(1, 80), (2, 50), (3, 50), (4, 20)], 0.5), 2.5)  # flat at 50%: its middle
        self.assertEqual(quantile([(1, 50), (2, 20)], 0.5), 1)  # exactly 50% at a threshold

    def test_a_quantile_outside_the_priced_thresholds_is_not_computable(self):
        self.assertIsNone(quantile([(3, 40), (5, 30), (7, 20)], 0.5))  # every threshold below 50%
        self.assertIsNone(quantile([(3, 90), (5, 80)], 0.5))
        self.assertIsNone(quantile([(3, 90)], 0.5))

    def test_the_expected_figure_and_its_spread(self):
        e = expected_figure([(3, 90), (5, 70), (7, 30), (9, 10)])
        self.assertEqual((e["median"], e["q25"], e["q75"], e["spread"]), (6.0, 4.5, 7.5, 3.0))
        e = expected_figure([(7, 30), (3, 90), (5, 70)])  # any order, and no 75th percentile
        self.assertEqual((e["median"], e["q75"], e["spread"]), (6.0, None, None))
        self.assertIsNone(expected_figure([(3, 40), (5, 30)]))
        # The plan reads the median from the priced thresholds: an unpriced one is left out, not the whole ladder
        e = expected_figure([(3, 90), (4, None), (5, 70), (7, 30), (9, 10)])
        self.assertEqual((e["median"], e["spread"]), (6.0, 3.0))
        self.assertIsNone(expected_figure([(3, None), (5, 30)]))  # 1 priced threshold brackets nothing


class SurpriseTests(unittest.TestCase):
    def test_a_beat_or_a_miss_against_the_expected_figure(self):
        expected = {"median": 6.0, "spread": 3.0}
        self.assertEqual(surprise(7, expected), {"outcome": "beat", "standardised": 1 / 3})
        self.assertEqual(surprise(4.5, expected), {"outcome": "miss", "standardised": -0.5})
        self.assertEqual(surprise(6, expected), {"outcome": None, "standardised": 0.0})  # equal: dropped
        self.assertEqual(surprise(7, {"median": 6.0, "spread": None}), {"outcome": "beat", "standardised": None})


if __name__ == "__main__":
    unittest.main()
