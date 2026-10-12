"""Reproduce a cited Q3 estimate; all source acquisitions are saved under runs.
Research prototype, not investment advice. No network, credentials, or market prices.
"""
import json
import math
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
LADDER = 'KXCAVA-26NOVREST'
open_data = json.loads((ROOT / "runs/replication/open-q3.json").read_text())
thresholds = next(x["thresholds"] for x in open_data["ladders"] if x["ladder"] == LADDER)
triage = json.loads((ROOT / "runs/replication/triage.json").read_text())["triage"]
report_date = next(x.get("report_date") for x in triage if x["ladder"] == LADDER) or "2026-11-10"
INPUTS = [{'url': 'https://uk.finance.yahoo.com/news/cava-group-reports-second-quarter-201000123.html', 'locator': 'paragraph-0005', 'excerpt': 'financial results for its fiscal second quarter ended July 12, 2026.', 'claim': 'Q2 ends July 12, 2026; twelve subsequent weeks end October 4, 2026 (calendar calculation).'}, {'url': 'https://uk.finance.yahoo.com/news/cava-group-reports-second-quarter-201000123.html', 'locator': 'paragraph-0661', 'excerpt': 'In a 52-week fiscal year, the first fiscal quarter contains sixteen weeks and the second, third, and fourth fiscal quarters each contain twelve weeks.', 'claim': 'Fiscal third quarter contains twelve weeks; model period is July 13 through October 4, 2026.'}, {'url': 'https://uk.finance.yahoo.com/news/cava-group-reports-second-quarter-201000123.html', 'locator': 'paragraph-0424', 'excerpt': 'The following table shows the growth in our company-owned CAVA Restaurant base:', 'claim': 'The reported restaurant-count table measures company-owned restaurants.'}, {'url': 'https://uk.finance.yahoo.com/news/cava-group-reports-second-quarter-201000123.html', 'locator': 'table-009', 'excerpt': 'Beginning of period 459 382 439 367 New CAVA Restaurant openings 17 16 38 31 Permanent closure — — (1 ) — End of period 476 398 476 398', 'claim': 'Q2 company-owned ending restaurants476 and seventeen openings; year-to-date one permanent closure.'}, {'url': 'https://markets.ft.com/data/announce/detail?dockey=600-202609231600BIZWIRE_USPRX____20260923_BW562355-1', 'locator': 'paragraph-0002', 'excerpt': 'today announced a significant achievement in the company’s continued national expansion as it commemorates its 500-restaurant footprint.', 'claim': 'September 23 observed brand footprint500; the milestone does not specify whether licensed airport restaurants are included.'}, {'url': 'https://finance.yahoo.com/markets/stocks/articles/cava-cava-q2-2026-earnings-225841627.html', 'locator': 'paragraph-0116', 'excerpt': 'Our airport locations are only licensed partner locations. We run all of our other restaurants.', 'claim': 'Ownership reconciliation: airport locations licensed, all other restaurants operated; milestone-to-company-owned difference remains uncertain.'}, {'url': 'https://finance.yahoo.com/markets/stocks/articles/cava-cava-q2-2026-earnings-225841627.html', 'locator': 'paragraph-0116', 'excerpt': 'Very excited to have Hartsfield open. We recently also opened at Logan Airport in Boston and not too long ago at LAX.', 'claim': 'Three named licensed airports; this statement does not certify the complete licensed-location count.'}]
METHOD = 'The reported metric is company-owned restaurants: Q2 ended July 12 with 476, while the September 23 milestone observes a 500-restaurant footprint 73 days later; fiscal Q3 ends October 4, twelve weeks after Q2. I use an explicitly subjective ownership mixture: 50% probability the milestone already excludes licensed stores, otherwise subtract 3/4/5 licensed stores with conditional weights 50%/30%/20% because three airports are named but the complete licensed count and footprint meaning remain unverified. I then add a Poisson count with rate (500-476)*11/73=3.616 for the eleven remaining days and subtract one closure with subjective 5% probability, with 95% weight on that count distribution and 5% on the same counts plus an independent rounded-normal reconciliation correction of mean zero and standard deviation five restaurants. The pace, ownership weights, closure probability and broad error component are subjective assumptions rather than measured frequencies, and strict exceedance integrates both count distributions; report_date November 10 is expected/assumed rather than company-announced, and this projection has material uncertainty from the unresolved brand-footprint/company-owned perimeter.'

rate = (500 - 476) * 11 / 73
ownership = {0: 0.5, 3: 0.25, 4: 0.15, 5: 0.10}
dist = {}
for licensed, weight in ownership.items():
    for openings in range(61):
        p = math.exp(-rate) * rate ** openings / math.factorial(openings)
        for closures, cp in [(0, 0.95), (1, 0.05)]:
            value = 500 - licensed + openings - closures
            dist[value] = dist.get(value, 0.0) + weight * p * cp
assert abs(sum(dist.values()) - 1) < 1e-12
# A subjective 5% broad scope/revision-error component prevents hard certainty
# when neither the full licensed-store perimeter nor closures were verified.
error_weight, correction_sd = 0.05, 5.0
chances = []
for s in thresholds:
    direct = sum(p for v, p in dist.items() if v > s)
    corrected = sum(p * 0.5 * math.erfc((s + 0.5 - v) / (correction_sd * math.sqrt(2))) for v, p in dist.items())
    chances.append({"strike": s, "above": round((1 - error_weight) * direct + error_weight * corrected, 8)})
result = {"ladder": LADDER, "report_date": report_date, "filed_at": datetime.now().astimezone().isoformat(timespec="seconds"), "chances": chances, "inputs": INPUTS, "method": METHOD}
output = ROOT / "runs/replication/estimates" / (LADDER + ".json")
output.write_text(json.dumps(result, indent=2, ensure_ascii=False) + "\n")
print(json.dumps({"written": str(output), "model_mean": globals().get("mu"), "chances": chances}, indent=2))
