"""Reproduce the cited Q3 estimate using saved mef-read command outputs; no network or keys."""
import json
import math
from pathlib import Path
from datetime import datetime, timezone
ROOT = Path(__file__).resolve().parents[3]
RESEARCH = ROOT / "runs/replication/research/accounts"
LADDER = 'KXHOOD-26NOVECVOL'
def citation(filename, url_fragment, locator, excerpt, claim):
    records = json.loads((RESEARCH / filename).read_text())["read"]
    record = next(r for r in records if url_fragment in r["url"])
    passage = next(p["text"] for p in record["passages"] if p["locator"] == locator)
    assert excerpt in passage, (locator, excerpt)
    return dict(url=record["url"], locator=locator, excerpt=excerpt, claim=claim)
def survival(cutoff, mean, sd):
    return 0.5 * math.erfc((cutoff - mean) / (sd * math.sqrt(2)))

# Observed July and August contract volumes in billions.
july, august = 6.1, 4.7
observed = july + august
september_mean = august * 30 / 31  # constant August daily rate, September's 30 days
cv = 0.35  # subjective positive-month uncertainty, not a fitted estimate
log_sd = math.sqrt(math.log1p(cv * cv))
log_mean = math.log(september_mean) - 0.5 * log_sd * log_sd
def september_survival(cutoff):
    if cutoff <= 0:
        return 1.0
    return survival(math.log(cutoff), log_mean, log_sd)
# Integrate independent assumed +/-0.05bn July/Aug rounding/revision errors.
# Final quarterly display assumed nearest 0.1bn, hence strict-above cutoff +0.05bn.
def probability(strike):
    n = 101
    return sum(september_survival(strike / 1e9 + 0.05 - observed -
                                 (-0.05 + (i+0.5)*0.1/n) - (-0.05 + (j+0.5)*0.1/n))
               for i in range(n) for j in range(n)) / (n*n)
inputs = [
 citation("hood-august.json", "menafn", "table-001",
          "Event Contracts Traded were 4.7 billion (down 23% from July 2026, up 15x year-over-year). ADVs were 152 million contracts",
          "August event-contract volume is 4.7bn; displayed daily volume is 152m contracts."),
 citation("hood-august.json", "menafn", "table-002",
          "August 2026 July 2026 M/M Change August 2025 Y/Y Change (M - in millions, B - in billions)",
          "Table columns distinguish August and July 2026 and their volume units."),
 citation("hood-august.json", "menafn", "table-002",
          "Event Contracts (B) 4.7 6.1 (23%) 0.3 +15x",
          "July 2026 event contracts are 6.1bn; adding August's 4.7bn gives 10.8bn measured Q3 volume."),
 citation("initial-read.json", "menafn", "paragraph-0007",
          "The information in this release is unaudited and the information for the months in the most recent fiscal quarter is preliminary, based on Robinhood's estimates, and subject to completion of financial closing procedures.",
          "The observed Q3 monthly figures are preliminary and may be revised."),
 citation("report-dates.json", "marketscreener", "paragraph-0003",
          "announced that it will release its third quarter 2026 financial results on Tuesday, October 27, 2026, after market close.",
          "The company-announced Q3 release date is October 27, 2026.")]

ladders = json.loads((ROOT / "runs/replication/open-q3.json").read_text())["ladders"]
thresholds = next(x["thresholds"] for x in ladders if x["ladder"] == LADDER)
output = dict(ladder=LADDER, report_date='2026-10-27', filed_at=datetime.now(timezone.utc).isoformat(),
              chances=[dict(strike=s, above=round(probability(s), 8)) for s in thresholds],
              inputs=inputs, method='Sum the observed July 6.1 billion and August 4.7 billion contracts, then model the unobserved September volume as a positive lognormal with mean 4.7 x 30/31 = 4.548387 billion (unchanged August daily rate) and subjective coefficient of variation 35%, giving mean Q3 volume 15.348387 billion. The CV is not fitted, allows September activity to differ materially, and the script integrates independent uniform +/-0.05 billion errors for each preliminary observed month to represent assumed rounding and small revisions. Assume the reported quarterly volume rounds to the nearest 0.1 billion, so a strictly-above outcome uses a latent total at least strike + 0.05 billion; broader revisions are only a model limitation, and checked refreshed indexes, attempted September releases and searches supplied no newer numerical measurement.')
assert all(a["above"] >= b["above"] for a,b in zip(output["chances"], output["chances"][1:]))
path = ROOT / "runs/replication/estimates" / (LADDER + ".json")
path.write_text(json.dumps(output, indent=2) + "\n")
print(json.dumps(dict(file=str(path), filed_at=output["filed_at"], chances=output["chances"]), indent=2))
