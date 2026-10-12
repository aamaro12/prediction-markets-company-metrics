"""Reproduce the cited Q3 estimate using saved mef-read command outputs; no network or keys."""
import json
import math
from pathlib import Path
from datetime import datetime, timezone
ROOT = Path(__file__).resolve().parents[3]
RESEARCH = ROOT / "runs/replication/research/accounts"
LADDER = 'KXETOR-26NOVFUNDED'
def citation(filename, url_fragment, locator, excerpt, claim):
    records = json.loads((RESEARCH / filename).read_text())["read"]
    record = next(r for r in records if url_fragment in r["url"])
    passage = next(p["text"] for p in record["passages"] if p["locator"] == locator)
    assert excerpt in passage, (locator, excerpt)
    return dict(url=record["url"], locator=locator, excerpt=excerpt, claim=claim)
def survival(cutoff, mean, sd):
    return 0.5 * math.erfc((cutoff - mean) / (sd * math.sqrt(2)))

mean, sd = 4.36 * 1000000, 100000
# Carry forward one measured Q3 endpoint; do not infer organic growth from acquisitions or YoY.
# Missing month, definition/preliminary revisions and acquisition integration reflected in subjective sd.
def probability(strike):
    return survival(strike + 5000, mean, sd)
inputs = [
 citation("etoro-observation.json", "businessinsider", "paragraph-0001",
          "is reporting the below selected monthly business metrics for August 2026.",
          "The release measures August 2026 business metrics."),
 citation("etoro-observation.json", "businessinsider", "item-0002",
          "Funded Accounts* were 4.36M, up 18% year-over-year.",
          "August funded accounts were 4.36m, matching the contract's funded-accounts metric."),
 citation("etoro-observation.json", "businessinsider", "paragraph-0002",
          "* Funded Accounts for August 2026 includes 110,000 from Zengo and Bit2C acquisitions. ** Metrics for August 2026 are estimated as of August 31, 2026. Numbers are rounded but percentages are based on unrounded numbers.",
          "The August endpoint includes 110k acquired accounts and is estimated and rounded."),
 citation("etoro-observation.json", "businessinsider", "paragraph-0010",
          "Funded Accounts: Funded Accounts are users who have successfully completed the onboarding requirements, activated their account, deposited funds, executed at least one trade, and maintain a positive account balance. For Zengo and Bit2C users, Funded Accounts are defined as users with a positive account balance.",
          "The funded-account definition includes a positive-balance requirement, with a distinct rule for acquired Zengo and Bit2C users."),
 citation("etoro-observation.json", "businessinsider", "paragraph-0003",
          "The selected preliminary data presented above is based on currently available information, has not been audited or reviewed, is subject to update and should not be extrapolated for future periods.",
          "The company warns its monthly observations are preliminary and should not be extrapolated."),
 citation("etoro-observation.json", "businessinsider", "paragraph-0003",
          "Final results and other business metrics for the full fiscal quarter will be available in our filings with the U.S. Securities and Exchange Commission (“SEC”) or otherwise publicly disclosed and might vary from the information in this press release.",
          "Final quarter metrics may differ from monthly preliminary data.")]

ladders = json.loads((ROOT / "runs/replication/open-q3.json").read_text())["ladders"]
thresholds = next(x["thresholds"] for x in ladders if x["ladder"] == LADDER)
output = dict(ladder=LADDER, report_date='2026-11-10', filed_at=datetime.now(timezone.utc).isoformat(),
              chances=[dict(strike=s, above=round(probability(s), 8)) for s in thresholds],
              inputs=inputs, method="Carry August's measured 4.36 million funded accounts forward as the September mean with no assumed net growth, and use a normal latent count with a subjective 100,000 standard deviation for the unobserved month, rounded inputs, preliminary revisions and the inclusion of 110,000 acquired accounts. This is an explicitly uncertain research projection despite the issuer's non-extrapolation warning, not an issuer forecast or a fitted interval; assume the quarterly figure rounds to the nearest 0.01 million and use P(latent count >= strike + 5,000) for strictly above. November 10, 2026 is an unverified expected report date used as a scheduling assumption, not a company announcement; refreshed issuer pages were blocked and the checked indexes/searches supplied no newer numeric measurement.")
assert all(a["above"] >= b["above"] for a,b in zip(output["chances"], output["chances"][1:]))
path = ROOT / "runs/replication/estimates" / (LADDER + ".json")
path.write_text(json.dumps(output, indent=2) + "\n")
print(json.dumps(dict(file=str(path), filed_at=output["filed_at"], chances=output["chances"]), indent=2))
