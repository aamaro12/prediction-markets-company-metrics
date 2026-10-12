"""Sources Codex reads, the passages a citation can point at, and the check that a quoted passage is where it says.

Every claim Codex makes about an event cites a document mef acquired: a URL, a locator such as paragraph-0004 and an
excerpt quoted word for word. A citation is checked against the saved extraction, never against the live page.
"""

import hashlib
import json
from pathlib import Path
import re

from .fetching import Fetcher, ReplayFetcher, load_fixture, resolve_user_agent, save_extraction, timestamp
from .html import Page
from .sources import public_url, publication, source_entry

MIN_EXCERPT_WORDS = 3
PUBLISHED = "published_at"  # the locator of a page's recorded publication time, which wire services keep in metadata
MAX_SOURCES = 200


def normal(text):
    return re.sub(r"\s+", " ", str(text)).strip()


def find_patterns(find):
    """--find's regular expressions, case-insensitive; a malformed one is the caller's error."""
    try:
        return [re.compile(f, re.I) for f in find]
    except re.error as error:
        raise ValueError(f"--find takes regular expressions: {error}") from None


def citable_units(extracted):
    """The passages of an extracted source that a citation can point at: (locator, text) pairs."""
    units = [(p.get("locator"), p["text"]) for p in extracted.get("paragraphs", []) + extracted.get("items", [])]
    units += [(t.get("locator"), t["text"]) for t in extracted.get("tables", [])]
    units += [
        (c.get("locator"), c["text"])
        for t in extracted.get("tables", [])
        for r in t.get("rows", [])
        for c in r.get("cells", [])
    ]
    return units


def acquire(fetcher, url):
    """Fetch a source, or reuse the saved copy, and save its citable extraction."""
    mode = "synthetic" if isinstance(fetcher, ReplayFetcher) else "live"
    rec = fetcher.fetch(public_url(url, synthetic=mode == "synthetic"), "document")
    source = source_entry(rec, url, mode)
    if rec["status"] != "ok":
        return source
    path = fetcher.directory / rec["local_path"]
    if path.suffix == ".pdf":
        import logging

        from pypdf import PdfReader
        from pypdf.errors import DependencyError, PyPdfError

        logging.getLogger("pypdf").setLevel(logging.ERROR)
        try:
            pages = PdfReader(path).pages[:300]
            extracted = {
                "title": url,
                "paragraphs": [
                    {"locator": f"page-{i + 1:03d}", "text": p.extract_text() or ""} for i, p in enumerate(pages)
                ],
                "tables": [],
            }
        except (PyPdfError, DependencyError, ValueError, OSError) as error:
            return {**source, "status": "unreadable_pdf", "error": type(error).__name__}
    elif path.suffix == ".html":
        page = Page(fetcher.text(rec), rec.get("final_url", url))
        extracted = {
            "title": page.title,
            "paragraphs": page.paragraphs(),
            "items": page.items(),
            "tables": page.tables(),
        }
        published = publication(page)
        if published:
            source["published_at"] = published
        if any(x in page.title.lower() for x in ("access denied", "just a moment", "request blocked")):
            source["status"] = "content_blocked"
    else:
        extracted = {"title": url, "paragraphs": [{"locator": "json", "text": fetcher.text(rec)}], "tables": []}
    source.update(save_extraction(fetcher.directory, source["id"], extracted))
    if source["status"] == "ok" and not citable_units(extracted):
        source["status"] = "no_citable_text"  # such as a page its scripts draw
    return source


def reader(sources, replay=None, user_agent=None, live=True):
    fixture = load_fixture(replay)
    if fixture is not None:
        return ReplayFetcher(sources, fixture)
    if not live:  # checking citations never fetches: an unread source fails rather than being read now
        return Fetcher(sources, resolve_user_agent(user_agent, live=False), max_requests=0)
    return Fetcher(sources, resolve_user_agent(user_agent), max_requests=MAX_SOURCES, min_interval=0.25)


def read_sources(urls, sources, find=(), replay=None, user_agent=None, limit=40):
    """Acquire sources and list the passages a citation can point at, with their locators."""
    fetcher = reader(sources, replay, user_agent)
    patterns = find_patterns(find)
    read = []
    for url in urls:
        source = acquire(fetcher, url)
        entry = {k: source[k] for k in ("url", "status", "published_at", "error") if source.get(k) is not None}
        if source.get("extracted_path"):
            units = citable_units(json.loads((Path(sources) / source["extracted_path"]).read_text()))
            passages = [
                {"locator": at, "text": body}
                for at, body in units
                if not patterns or any(p.search(body) for p in patterns)
            ]
            entry.update(matched=len(passages), passages=passages[:limit])
        read.append(entry)
    return {"sources": str(Path(sources).resolve()), "requests": fetcher.requests, "read": read}


def check_citation(citation, sources, replay=None):
    """A citation's excerpt, found at its locator in the saved extraction of a source mef acquired."""
    if not isinstance(citation, dict) or not all(
        str(citation.get(k) or "").strip() for k in ("url", "locator", "excerpt")
    ):
        raise ValueError("A citation needs a url, a locator and an excerpt")
    if citation["locator"] not in ("json", PUBLISHED) and len(citation["excerpt"].split()) < MIN_EXCERPT_WORDS:
        raise ValueError(f"Quote at least {MIN_EXCERPT_WORDS} words from {citation['url']}")
    source = acquire(reader(sources, replay, live=False), citation["url"])
    if source.get("status") != "ok":
        raise ValueError(f"{citation['url']} was not read with mef read ({source.get('status')})")
    if citation["locator"] == PUBLISHED:
        try:
            same = abs((timestamp(source.get("published_at") or "") - timestamp(citation["excerpt"])).total_seconds())
        except ValueError:
            same = None
        if same is None or same >= 60:
            raise ValueError(f"{citation['excerpt']} is not the publication time {citation['url']} records")
        return {**citation, "sha256": source.get("sha256"), "published_at": source.get("published_at")}
    extracted = Path(sources) / source["extracted_path"]
    if hashlib.sha256(extracted.read_bytes()).hexdigest() != source.get("extracted_sha256"):
        raise ValueError(f"The saved extraction of {citation['url']} changed")
    units = citable_units(json.loads(extracted.read_text()))
    texts = [text for at, text in units if at == citation["locator"]]
    if not texts:
        raise ValueError(f"Locator {citation['locator']} is not in {citation['url']}")
    excerpt = normal(citation["excerpt"]).casefold()
    if not any(excerpt in normal(t).casefold() for t in texts):
        raise ValueError(f"The excerpt is not at {citation['locator']} in {citation['url']}")
    return {**citation, "sha256": source.get("sha256"), "published_at": source.get("published_at")}


TIME_OF_DAY = re.compile(
    r"\b\d{1,2}[:.]\d{2}\s*(?:a\.?m\.?|p\.?m\.?|et|edt|est)?|\b(?:before|after)\s+(?:the\s+)?(?:u\.s\.\s+)?"
    r"(?:stock\s+)?market\s+(?:opens?|closes?|close|open)|\bpre-?market\b|\bafter\s+the\s+close\b",
    re.I,
)


def check_verification(v, sources, replay=None):
    """Codex's verification of 1 ladder: the report's time and the published figure, each cited, and whether the
    figure matches the contract's rules. Returns the checked record, or raises with the reason."""
    for key in ("ladder", "report_time", "report_citations", "figure_as_published", "figure_citation"):
        if not v.get(key):
            raise ValueError(f"{v.get('ladder')}: {key} is missing")
    try:
        when = timestamp(v["report_time"])
    except ValueError:
        raise ValueError(f"{v['ladder']}: report_time needs its offset, such as -04:00") from None
    report = [check_citation(c, sources, replay) for c in v["report_citations"]]
    stamps = [c for c in report if c["locator"] == PUBLISHED]
    if any(abs((timestamp(c["excerpt"]) - when).total_seconds()) >= 60 for c in stamps):
        raise ValueError(f"{v['ladder']}: report_time does not match the cited publication time")
    texts = " ".join(normal(c["excerpt"]) for c in report if c["locator"] != PUBLISHED)
    if not stamps and not (str(when.year) in texts and re.search(rf"(?<!\d)0?{when.day}(?!\d)", texts)):
        raise ValueError(f"{v['ladder']}: no report citation states the report's date")
    figure = check_citation(v["figure_citation"], sources, replay)
    digits = re.sub(r"[^\d.]", "", str(v["figure_as_published"]))
    if not digits or digits not in re.sub(r"[^\d.]", "", figure["excerpt"]):
        raise ValueError(f"{v['ladder']}: the figure citation does not contain {v['figure_as_published']}")
    if isinstance(v.get("figure_value"), bool) or not isinstance(v.get("figure_value"), (int, float)):
        raise ValueError(
            f"{v['ladder']}: figure_value must be the published figure as a number in the contract's units"
        )
    if not isinstance(v.get("matches_contract"), bool):
        raise ValueError(f"{v['ladder']}: matches_contract must be true or false")
    if not v["matches_contract"] and not str(v.get("mismatch") or "").strip():
        raise ValueError(f"{v['ladder']}: a mismatch needs its description")
    return {
        **v,
        "report_time": when.isoformat(),
        "time_of_day_cited": bool(stamps) or bool(TIME_OF_DAY.search(texts)),
        "report_citations": report,
        "figure_citation": figure,
    }
