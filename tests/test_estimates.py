"""Codex's estimates for the replication: checked before the report, scored after it against the market's prices."""

import unittest

from mef.estimates import check_estimate, crps

LADDER = {"ladder": "KXSCHW-26OCTACCTS", "thresholds": [40_000_000, 40_300_000, 40_600_000]}


def estimate(**changes):
    return {
        "ladder": "KXSCHW-26OCTACCTS",
        "report_date": "2026-10-15",
        "filed_at": "2026-10-14T03:00:00+00:00",  # 23:00 New York time on the 13th
        "chances": [
            {"strike": 40_000_000, "above": 0.8},
            {"strike": 40_300_000, "above": 0.5},
            {"strike": 40_600_000, "above": 0.1},
        ],
        "inputs": [],
        "method": "August's level plus September's typical increment.",
        **changes,
    }


class CheckTests(unittest.TestCase):
    def test_a_valid_estimate_passes(self):
        self.assertEqual(check_estimate(estimate(), [LADDER], sources=None)["ladder"], "KXSCHW-26OCTACCTS")

    def test_each_rule_refuses_what_it_should(self):
        cases = [
            ({"ladder": "KXNOPE"}, "not an open third-quarter ladder"),
            ({"chances": estimate()["chances"][:2]}, "every threshold"),
            (
                {
                    "chances": [
                        {"strike": s, "above": a} for s, a in ((40_000_000, 0.5), (40_300_000, 0.6), (40_600_000, 0.1))
                    ]
                },
                "fall as the threshold rises",
            ),
            (
                {
                    "chances": [
                        {"strike": s, "above": a} for s, a in ((40_000_000, 1.2), (40_300_000, 0.5), (40_600_000, 0.1))
                    ]
                },
                "between 0 and 1",
            ),
            ({"filed_at": "2026-10-15T05:00:00+00:00"}, "before midnight New York time"),  # 01:00 on report day
            ({"method": " "}, "method"),
        ]
        for change, message in cases:
            with self.subTest(message=message), self.assertRaisesRegex(ValueError, message):
                check_estimate(estimate(**change), [LADDER], sources=None)


class ScoreTests(unittest.TestCase):
    def test_the_score_weighs_each_squared_gap_by_the_distance_to_the_next_threshold(self):
        strikes = [10, 20, 40]
        outcomes = [1, 1, 0]  # the figure was between 20 and 40
        perfect = crps([1.0, 1.0, 0.0], strikes, outcomes)
        self.assertEqual(perfect, 0.0)
        # gaps 0.2, 0.5 and 0.1, weighted by 10, 20 and 20 (the last threshold reuses the spacing before it)
        self.assertAlmostEqual(crps([0.8, 0.5, 0.1], strikes, outcomes), 0.04 * 10 + 0.25 * 20 + 0.01 * 20)
        self.assertLess(crps([0.9, 0.8, 0.1], strikes, outcomes), crps([0.8, 0.5, 0.1], strikes, outcomes))


if __name__ == "__main__":
    unittest.main()
