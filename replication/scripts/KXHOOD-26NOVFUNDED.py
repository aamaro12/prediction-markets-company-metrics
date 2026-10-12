"""Reproduce the cited Q3 estimate using saved mef-read command outputs; no network or keys."""
import json
import math
from pathlib import Path
from datetime import datetime, timezone
ROOT = Path(__file__).resolve().parents[3]
RESEARCH = ROOT / "runs/replication/research/accounts"
LADDER = 'KXHOOD-26NOVFUNDED'
def citation(filename, url_fragment, locator, excerpt, claim):
    records = json.loads((RESEARCH / filename).read_text())["read"]
    record = next(r for r in records if url_fragment in r["url"])
    passage = next(p["text"] for p in record["passages"] if p["locator"] == locator)
    assert excerpt in passage, (locator, excerpt)
    return dict(url=record["url"], locator=locator, excerpt=excerpt, claim=claim)
def survival(cutoff, mean, sd):
    return 0.5 * math.erfc((cutoff - mean) / (sd * math.sqrt(2)))

august = 28.6 * 1000000
increment = 120000
mean, sd = august + increment, 150000
# Subjective normal missing-month/revision uncertainty and assumed nearest 0.1m quarterly display.
def probability(strike):
    return survival(strike + 50000, mean, sd)
inputs = [
 citation("hood-august.json", "menafn", "table-001",
          "today reported select monthly operating data for August 2026. Funded Customers at the end of August were 28.6 million (up approximately 120 thousand from the end of July 2026, up approximately 1.90 million year-over-year).",
          "August 2026 funded customers are 28.6m and August's net addition versus July is approximately 120k."),
 citation("initial-read.json", "menafn", "paragraph-0007",
          "The information in this release is unaudited and the information for the months in the most recent fiscal quarter is preliminary, based on Robinhood's estimates, and subject to completion of financial closing procedures.",
          "The observed Q3 monthly figures are preliminary and may be revised."),
 citation("hood-august.json", "menafn", "paragraph-0004",
          "Funded Customers do not include Trump Accounts.",
          "The measured funded-customer series excludes Trump Accounts."),
 citation("report-dates.json", "marketscreener", "paragraph-0003",
          "announced that it will release its third quarter 2026 financial results on Tuesday, October 27, 2026, after market close.",
          "The company-announced Q3 release date is October 27, 2026.")]

ladders = json.loads((ROOT / "runs/replication/open-q3.json").read_text())["ladders"]
thresholds = next(x["thresholds"] for x in ladders if x["ladder"] == LADDER)
output = dict(ladder=LADDER, report_date='2026-10-27', filed_at=datetime.now(timezone.utc).isoformat(),
              chances=[dict(strike=s, above=round(probability(s), 8)) for s in thresholds],
              inputs=inputs, method="Add the observed approximately 120,000 July-to-August increase to August's 28.6 million funded customers to project the unobserved September endpoint at 28.72 million, then use a normal latent count with subjective standard deviation 150,000. This standard deviation is not fitted and covers uncertain September net additions, the rounded August observation and preliminary-data revisions; assume quarterly reporting rounds to the nearest 0.1 million and calculate P(latent count >= strike + 50,000) for strictly above. Refreshed issuer indexes and attempted September releases were blocked and the checked searches yielded no newer numerical measurement, so September growth remains a projection.")
assert all(a["above"] >= b["above"] for a,b in zip(output["chances"], output["chances"][1:]))
path = ROOT / "runs/replication/estimates" / (LADDER + ".json")
path.write_text(json.dumps(output, indent=2) + "\n")
print(json.dumps(dict(file=str(path), filed_at=output["filed_at"], chances=output["chances"]), indent=2))
