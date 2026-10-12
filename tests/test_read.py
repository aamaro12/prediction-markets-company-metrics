"""Codex cites what it read: a passage is checked at its locator in the saved extraction, and a verification of a
ladder must cite the report's date and the published figure."""

from pathlib import Path
import tempfile
import unittest

from mef.fetching import save_json
from mef.read import check_citation, check_verification, read_sources

RELEASE = "https://ir.example.invalid/q2-results"
BODY = (
    "<html><head><title>CAVA Reports Second Quarter 2026 Results</title>"
    '<meta property="article:published_time" content="2026-08-11T20:05:00+00:00"></head><body>'
    "<p>WASHINGTON, Aug. 11, 2026 -- CAVA Group, Inc. today reported results after the market close.</p>"
    "<p>Same restaurant sales growth was 9.0% in the second quarter.</p></body></html>"
)


class ReadTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.out = Path(self.tmp.name)
        self.fixture = self.out / "fixture.json"
        save_json(
            self.fixture,
            {
                "mode": "synthetic",
                "as_of": "2026-10-12T00:00:00+00:00",
                "responses": {RELEASE: {"body": BODY, "content_type": "text/html"}},
            },
        )
        self.sources = self.out / "sources"
        self.read = read_sources([RELEASE], self.sources, find=["restaurant sales"], replay=self.fixture)

    def tearDown(self):
        self.tmp.cleanup()

    def cite(self, locator, excerpt):
        return {"url": RELEASE, "locator": locator, "excerpt": excerpt}

    def test_read_lists_the_passages_a_citation_can_point_at(self):
        (entry,) = self.read["read"]
        self.assertEqual(entry["status"], "ok")
        self.assertEqual(
            entry["passages"],
            [{"locator": "paragraph-0002", "text": "Same restaurant sales growth was 9.0% in the second quarter."}],
        )

    def test_a_citation_is_found_at_its_locator_or_refused(self):
        ok = check_citation(
            self.cite("paragraph-0002", "Same restaurant sales growth was 9.0%"), self.sources, self.fixture
        )
        self.assertEqual(ok["locator"], "paragraph-0002")
        for citation, message in (
            (self.cite("paragraph-0001", "Same restaurant sales growth"), "not at paragraph-0001"),
            (self.cite("paragraph-0009", "Same restaurant sales growth"), "not in"),
            (self.cite("paragraph-0002", "grew 12%"), "at least 3 words"),
            (
                {"url": "https://ir.example.invalid/other", "locator": "paragraph-0001", "excerpt": "a b c d"},
                "not read",
            ),
        ):
            with self.subTest(message=message), self.assertRaisesRegex(ValueError, message):
                check_citation(citation, self.sources, self.fixture)

    def test_a_verification_cites_the_reports_date_and_the_figure(self):
        v = {
            "ladder": "KXCAVA-26AUGCOMP",
            "report_time": "2026-08-11T16:05:00-04:00",
            "report_citations": [
                self.cite(
                    "paragraph-0001", "Aug. 11, 2026 -- CAVA Group, Inc. today reported results after the market close"
                )
            ],
            "figure_as_published": "9.0%",
            "figure_value": 9.0,
            "figure_citation": self.cite("paragraph-0002", "Same restaurant sales growth was 9.0%"),
            "matches_contract": True,
        }
        checked = check_verification(v, self.sources, self.fixture)
        self.assertTrue(checked["time_of_day_cited"])  # "after the market close"
        with self.assertRaisesRegex(ValueError, "does not contain 9.4%"):
            check_verification({**v, "figure_as_published": "9.4%"}, self.sources, self.fixture)
        with self.assertRaisesRegex(ValueError, "states the report's date"):
            check_verification({**v, "report_time": "2026-08-12T07:00:00-04:00"}, self.sources, self.fixture)
        with self.assertRaisesRegex(ValueError, "needs its offset"):
            check_verification({**v, "report_time": "2026-08-11T16:05:00"}, self.sources, self.fixture)
        with self.assertRaisesRegex(ValueError, "mismatch needs"):
            check_verification({**v, "matches_contract": False}, self.sources, self.fixture)
        with self.assertRaisesRegex(ValueError, "figure_value must be"):
            check_verification({**v, "figure_value": "9.0"}, self.sources, self.fixture)
        flagged = {**v, "matches_contract": False, "mismatch": "The contract counts a different segment"}
        self.assertFalse(check_verification(flagged, self.sources, self.fixture)["matches_contract"])
        no_time = {**v, "report_citations": [self.cite("paragraph-0001", "WASHINGTON, Aug. 11, 2026 -- CAVA Group")]}
        self.assertFalse(check_verification(no_time, self.sources, self.fixture)["time_of_day_cited"])

    def test_a_wire_services_recorded_publication_time_can_be_cited_exactly(self):
        # Wire services keep the release time in the page's metadata, outside any paragraph a reader lists
        stamp = {"url": RELEASE, "locator": "published_at", "excerpt": "2026-08-11T20:05:00+00:00"}
        v = {
            "ladder": "KXCAVA-26AUGCOMP",
            "report_time": "2026-08-11T16:05:00-04:00",
            "report_citations": [stamp],
            "figure_as_published": "9.0%",
            "figure_value": 9.0,
            "figure_citation": self.cite("paragraph-0002", "Same restaurant sales growth was 9.0%"),
            "matches_contract": True,
        }
        checked = check_verification(v, self.sources, self.fixture)
        self.assertTrue(checked["time_of_day_cited"])
        with self.assertRaisesRegex(ValueError, "not the publication time"):
            check_verification(
                {**v, "report_citations": [{**stamp, "excerpt": "2026-08-11T19:00:00+00:00"}]},
                self.sources,
                self.fixture,
            )
        with self.assertRaisesRegex(ValueError, "does not match"):  # the claimed time must be the recorded one
            check_verification({**v, "report_time": "2026-08-11T09:00:00-04:00"}, self.sources, self.fixture)


if __name__ == "__main__":
    unittest.main()
