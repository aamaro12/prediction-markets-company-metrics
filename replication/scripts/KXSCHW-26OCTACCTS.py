"""Reproduce the cited Q3 estimate using saved mef-read command outputs; no network or keys."""
import json
import math
from pathlib import Path
from datetime import datetime, timezone
ROOT = Path(__file__).resolve().parents[3]
RESEARCH = ROOT / "runs/replication/research/accounts"
LADDER = 'KXSCHW-26OCTACCTS'
def citation(filename, url_fragment, locator, excerpt, claim):
    records = json.loads((RESEARCH / filename).read_text())["read"]
    record = next(r for r in records if url_fragment in r["url"])
    passage = next(p["text"] for p in record["passages"] if p["locator"] == locator)
    assert excerpt in passage, (locator, excerpt)
    return dict(url=record["url"], locator=locator, excerpt=excerpt, claim=claim)
def survival(cutoff, mean, sd):
    return 0.5 * math.erfc((cutoff - mean) / (sd * math.sqrt(2)))

# Exact table observations, in thousands; July and August are observed Q3 endpoints.
june, july, august = 39802 * 1000, 39940 * 1000, 40090 * 1000
net_additions = [july - june, august - july]
mean = august + sum(net_additions) / len(net_additions)  # 40,234,000
sd = 75000  # Subjective missing-month / revisions uncertainty, not fitted.
# Uncertain quarterly display precision: equally weight nearest thousand and nearest 0.1m.
# At a lattice strike, strict-above rounded value requires latent value >= strike + half-step.
def probability(strike):
    return 0.5 * survival(strike + 500, mean, sd) + 0.5 * survival(strike + 50000, mean, sd)
inputs = [
 citation("schwab-details.json", "schwab-reports-monthly", "table-001",
          "2025 2026 Change Aug Sep Oct Nov Dec Jan Feb Mar Apr May Jun Jul Aug Mo. Yr.",
          "The monthly table columns identify June, July and August 2026."),
 citation("schwab-details.json", "schwab-reports-monthly", "table-001",
          "Client Accounts (at month end, in thousands) Active Brokerage Accounts 37,798 37,963 38,145 38,266 38,506 38,730 38,925 39,099 39,300 39,536 39,802 39,940 40,090",
          "June, July and August active brokerage account counts are 39.802m, 39.940m and 40.090m; the observed Q3 month-end series measures the contract metric."),
 citation("report-dates.json", "schwab-announces", "paragraph-0002",
          "The Charles Schwab Corporation announced today that it has scheduled a Fall Business Update for institutional investors on Thursday, October 15th.",
          "October 15 is the announced Fall Business Update date; it is not an explicitly verified earnings-release date.")]

ladders = json.loads((ROOT / "runs/replication/open-q3.json").read_text())["ladders"]
thresholds = next(x["thresholds"] for x in ladders if x["ladder"] == LADDER)
output = dict(ladder=LADDER, report_date='2026-10-15', filed_at=datetime.now(timezone.utc).isoformat(),
              chances=[dict(strike=s, above=round(probability(s), 8)) for s in thresholds],
              inputs=inputs, method="Project the unobserved September account count from August's 40.090 million plus the mean of the July and August net additions (138,000 and 150,000), giving a normal latent count with mean 40.234 million and a subjective 75,000 standard deviation for missing-month and revision uncertainty, not a fitted confidence interval. For reporting precision uncertainty, equally weight rounding to the nearest 1,000 and nearest 100,000 accounts, and calculate strict-above chances using each strike plus half its rounding step. October 15, 2026 is an expected report date inferred from the announced Fall Business Update, not a verified earnings-release announcement; the latest checked public measurement is August, with refreshed issuer pages blocked and no newer measurement in the checked searches.")
assert all(a["above"] >= b["above"] for a,b in zip(output["chances"], output["chances"][1:]))
path = ROOT / "runs/replication/estimates" / (LADDER + ".json")
path.write_text(json.dumps(output, indent=2) + "\n")
print(json.dumps(dict(file=str(path), filed_at=output["filed_at"], chances=output["chances"]), indent=2))
