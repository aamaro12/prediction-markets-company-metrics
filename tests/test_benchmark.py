"""The market's expected figure against 2 simple forecasts: the same quarter a year earlier, and the quarter before.
Codex cites each earlier figure from the company's own publications, and Python checks every citation."""

from pathlib import Path
import tempfile
import unittest

from mef.benchmark import benchmark, check_comparative
from mef.fetching import save_json
from mef.read import read_sources

RELEASE = "https://ir.example.invalid/q2-results"
BODY = (
    "<html><head><title>CAVA Reports Second Quarter 2026 Results</title></head><body>"
    "<p>Same restaurant sales growth was 9.0%, compared with 14.4% in the second quarter of 2025.</p>"
    "<p>Same restaurant sales growth was 10.8% in the first quarter of 2026.</p></body></html>"
)


class ComparativeTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        out = Path(self.tmp.name)
        self.fixture = out / "fixture.json"
        save_json(
            self.fixture,
            {
                "mode": "synthetic",
                "as_of": "2026-10-12T00:00:00+00:00",
                "responses": {RELEASE: {"body": BODY, "content_type": "text/html"}},
            },
        )
        self.sources = out / "sources"
        read_sources([RELEASE], self.sources, replay=self.fixture)

    def tearDown(self):
        self.tmp.cleanup()

    def earlier(self, period, published, value, locator, excerpt):
        return {
            "period": period,
            "as_published": published,
            "value": value,
            "citation": {"url": RELEASE, "locator": locator, "excerpt": excerpt},
        }

    def entry(self, **changes):
        return {
            "ladder": "KXCAVA-26AUGCOMP",
            "year_ago": self.earlier("Q2 2025", "14.4%", 14.4, "paragraph-0001", "compared with 14.4% in the second"),
            "previous_quarter": self.earlier(
                "Q1 2026", "10.8%", 10.8, "paragraph-0002", "Same restaurant sales growth was 10.8%"
            ),
            **changes,
        }

    def test_each_earlier_figure_is_cited_and_checked(self):
        checked = check_comparative(self.entry(), self.sources, self.fixture)
        self.assertEqual(checked["year_ago"]["value"], 14.4)
        self.assertEqual(checked["previous_quarter"]["citation"]["locator"], "paragraph-0002")
        only_one = check_comparative(self.entry(previous_quarter=None), self.sources, self.fixture)
        self.assertIsNone(only_one["previous_quarter"])

    def test_an_earlier_figure_is_refused_unless_its_citation_states_it(self):
        wrong = self.earlier("Q2 2025", "15.1%", 15.1, "paragraph-0001", "compared with 14.4% in the second")
        for changes, message in (
            ({"year_ago": None, "previous_quarter": None}, "cites neither"),
            ({"year_ago": wrong}, "does not contain 15.1%"),
            ({"year_ago": {**self.entry()["year_ago"], "value": "14.4"}}, "value must be"),
            ({"year_ago": {**self.entry()["year_ago"], "period": ""}}, "period"),
        ):
            with self.subTest(message=message), self.assertRaisesRegex(ValueError, message):
                check_comparative(self.entry(**changes), self.sources, self.fixture)


class BenchmarkTests(unittest.TestCase):
    def test_the_market_and_each_simple_forecast_are_compared_on_the_same_ladders(self):
        rows = [  # figure 100: the market's median 101, the year-ago 90, the quarter before 99.5
            {"ladder": "A", "excluded": None, "figure": 100.0, "expected": {"median": 101.0}},
            {"ladder": "B", "excluded": None, "figure": 50.0, "expected": {"median": 45.0}},
            {"ladder": "C", "excluded": None, "figure": 10.0, "expected": {"median": 10.2}},
            {"ladder": "D", "excluded": "report time not cited", "figure": 10.0, "expected": {"median": 99.0}},
        ]
        earlier = {
            "A": {"year_ago": {"value": 90.0}, "previous_quarter": {"value": 99.5}},
            "B": {"year_ago": {"value": 40.0}, "previous_quarter": None},
            "D": {"year_ago": {"value": 10.0}, "previous_quarter": {"value": 10.0}},
        }
        result = benchmark(rows, earlier)
        year = result["year_ago"]
        self.assertEqual((year["n"], year["market_closer"], year["forecast_closer"], year["ties"]), (2, 2, 0, 0))
        self.assertAlmostEqual(year["market_median_gap_share"], (0.01 + 0.10) / 2)
        self.assertAlmostEqual(year["forecast_median_gap_share"], (0.10 + 0.20) / 2)
        before = result["previous_quarter"]
        self.assertEqual((before["n"], before["market_closer"], before["forecast_closer"]), (1, 0, 1))
        self.assertEqual(result["kept"], 3)  # D is excluded, as in the accuracy test

    def test_growth_rates_are_also_compared_in_points(self):
        rows = [  # a share of a small rate inflates every gap, so rates are also compared in points
            {
                "ladder": "R",
                "title": "CAVA same restaurant sales growth in Q2",
                "excluded": None,
                "figure": 0.5,
                "expected": {"median": 1.0},
            },
            {
                "ladder": "S",
                "title": "Sweetgreen profit margin in Q2",
                "excluded": None,
                "figure": 4.0,
                "expected": {"median": 3.0},
            },
            {
                "ladder": "N",
                "title": "Southwest Airlines Company seats flown in Q2",
                "excluded": None,
                "figure": 50.0,
                "expected": {"median": 49.0},
            },
        ]
        earlier = {
            "R": {"year_ago": {"value": 3.5}},
            "S": {"year_ago": {"value": 3.5}},
            "N": {"year_ago": {"value": 40.0}},
        }
        rates = benchmark(rows, earlier)["year_ago"]["rates"]
        self.assertEqual((rates["n"], rates["market_closer"], rates["forecast_closer"]), (2, 1, 1))
        self.assertAlmostEqual(rates["market_median_gap_points"], 0.75)
        self.assertAlmostEqual(rates["forecast_median_gap_points"], 1.75)


if __name__ == "__main__":
    unittest.main()
