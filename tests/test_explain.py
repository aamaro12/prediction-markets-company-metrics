"""The plan's 10 largest results-day moves against the surprise, each explained by Codex from news published by the
end of that day, with every citation checked."""

from pathlib import Path
import tempfile
import unittest

from mef.explain import against_surprise, check_explanation
from mef.fetching import save_json
from mef.read import read_sources

ON_THE_DAY = "https://news.example.invalid/guidance"
DAY_AFTER = "https://news.example.invalid/analysis"
UNDATED = "https://news.example.invalid/undated"


def page(published, text):
    meta = f'<meta property="article:published_time" content="{published}">' if published else ""
    return f"<html><head><title>News</title>{meta}</head><body><p>{text}</p></body></html>"


def event(ladder, outcome, move):
    return {
        "ladder": ladder,
        "company": ladder,
        "results_day": "2026-08-12",
        "outcome": outcome,
        "returns": {"results_day": move},
    }


class AgainstTests(unittest.TestCase):
    def test_the_largest_moves_against_the_surprise_come_first(self):
        events = [
            event("A", "beat", 0.20),  # with the surprise: left out
            event("B", "beat", -0.05),
            event("C", "miss", 0.12),
            event("D", "miss", -0.30),  # with the surprise: left out
            event("E", "beat", -0.12),
            {**event("F", "miss", None)},
        ]
        self.assertEqual([e["ladder"] for e in against_surprise(events, 2)], ["C", "E"])  # a tie goes by ladder
        self.assertEqual([e["ladder"] for e in against_surprise(events, 10)], ["C", "E", "B"])


class ExplanationTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        out = Path(self.tmp.name)
        self.fixture = out / "fixture.json"
        responses = {
            ON_THE_DAY: page("2026-08-12T14:00:00+00:00", "Shares fell after the company cut its full-year guidance."),
            DAY_AFTER: page("2026-08-13T14:00:00+00:00", "Analysts said the guidance cut drove the fall in shares."),
            UNDATED: page(None, "The guidance cut drove the fall in shares, analysts said."),
        }
        save_json(
            self.fixture,
            {
                "mode": "synthetic",
                "as_of": "2026-10-12T00:00:00+00:00",
                "responses": {u: {"body": b, "content_type": "text/html"} for u, b in responses.items()},
            },
        )
        self.sources = out / "sources"
        read_sources(list(responses), self.sources, replay=self.fixture)
        self.event = event("E", "beat", -0.12)

    def tearDown(self):
        self.tmp.cleanup()

    def entry(self, url, excerpt, **changes):
        cite = {"url": url, "locator": "paragraph-0001", "excerpt": excerpt}
        return {"ladder": "E", "explanation": "The company cut its full-year guidance.", "citations": [cite], **changes}

    def test_an_explanation_cites_news_published_by_the_end_of_results_day(self):
        checked = check_explanation(
            self.entry(ON_THE_DAY, "Shares fell after the company cut its full-year guidance"),
            self.event,
            self.sources,
            self.fixture,
        )
        self.assertEqual(checked["citations"][0]["published_at"][:10], "2026-08-12")
        self.assertEqual((checked["outcome"], checked["move"]), ("beat", -0.12))

    def test_later_undated_or_unexplained_entries_are_refused(self):
        for entry, message in (
            (self.entry(DAY_AFTER, "Analysts said the guidance cut drove the fall"), "after results day"),
            (self.entry(UNDATED, "The guidance cut drove the fall in shares"), "records no publication time"),
            (self.entry(ON_THE_DAY, "Shares fell after the company cut", explanation=" "), "needs its explanation"),
            (self.entry(ON_THE_DAY, "Shares fell after the company cut", citations=[]), "needs a citation"),
        ):
            with self.subTest(message=message), self.assertRaisesRegex(ValueError, message):
                check_explanation(entry, self.event, self.sources, self.fixture)


if __name__ == "__main__":
    unittest.main()
