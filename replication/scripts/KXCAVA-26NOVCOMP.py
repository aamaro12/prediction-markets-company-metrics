"""Reproduce a cited Q3 estimate; all source acquisitions are saved under runs.
Research prototype, not investment advice. No network, credentials, or market prices.
"""
import json
import math
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
LADDER = 'KXCAVA-26NOVCOMP'
open_data = json.loads((ROOT / "runs/replication/open-q3.json").read_text())
thresholds = next(x["thresholds"] for x in open_data["ladders"] if x["ladder"] == LADDER)
triage = json.loads((ROOT / "runs/replication/triage.json").read_text())["triage"]
report_date = next(x.get("report_date") for x in triage if x["ladder"] == LADDER) or "2026-11-10"
INPUTS = [{'url': 'https://uk.finance.yahoo.com/news/cava-group-reports-second-quarter-201000123.html', 'locator': 'paragraph-0005', 'excerpt': 'financial results for its fiscal second quarter ended July 12, 2026.', 'claim': 'Q2 ends July 12, 2026; twelve subsequent weeks end October 4, 2026 (calendar calculation).'}, {'url': 'https://uk.finance.yahoo.com/news/cava-group-reports-second-quarter-201000123.html', 'locator': 'paragraph-0661', 'excerpt': 'In a 52-week fiscal year, the first fiscal quarter contains sixteen weeks and the second, third, and fourth fiscal quarters each contain twelve weeks.', 'claim': 'Fiscal third quarter contains twelve weeks; model period is July 13 through October 4, 2026.'}, {'url': 'https://finance.yahoo.com/markets/stocks/articles/cava-cava-q2-2026-earnings-225841627.html', 'locator': 'paragraph-0003', 'excerpt': 'Tuesday, Aug. 11, 2026 at 5:00 p.m. ET', 'claim': 'Observed weekly sales-band statements were made August 11, within fiscal Q3.'}, {'url': 'https://finance.yahoo.com/markets/stocks/articles/cava-cava-q2-2026-earnings-225841627.html', 'locator': 'paragraph-0122', 'excerpt': 'Tricia Tolivar: Yes. So it dipped initially to flat to positive and then each week sequentially got better and the last week was a mid-single-digit same restaurant sales.', 'claim': 'Partial fiscal-Q3 weekly observations: initially flat-to-positive, sequential recovery, latest observed week mid-single-digit; no exact weekly percentages or full-quarter average supplied.'}, {'url': 'https://finance.yahoo.com/markets/stocks/articles/cava-cava-q2-2026-earnings-225841627.html', 'locator': 'paragraph-0037', 'excerpt': 'our same restaurant sales performance has recovered to mid-single digits.', 'claim': 'Latest observed weekly band in checked later-period searches remains this August 11 statement; projection requires assumptions for the remaining quarter.'}]
METHOD = 'I use fiscal Q3 July 13–October 4, twelve weeks after the cited July 12 Q2 end, and assume the August 11 comments summarize its first four completed weeks; initial flat-to-positive and latest mid-single-digit bands are subjective midpoints 1% and 5%, with a linear recovery averaging 3% across those four weeks. I assume the eight unobserved weeks average 5%, yielding (4*3+8*5)/12=4.333% and use a subjective normal quarterly standard deviation 1.5 percentage points for persistence, band interpretation, unequal sales weights and remaining-period uncertainty; this is a projection of observed weekly bands, not the full-year guidance. For a one-decimal reported percentage, P(reported > strike) uses a 0.05-point rounding correction; no later measured weekly band was verified in the checked sources, and report_date November 10 is expected/assumed rather than company-announced.'

mu, sigma = (4 * 3.0 + 8 * 5.0) / 12, 1.5
chances = [{"strike": s, "above": round(0.5 * math.erfc((s + 0.05 - mu) / (sigma * math.sqrt(2))), 8)} for s in thresholds]
result = {"ladder": LADDER, "report_date": report_date, "filed_at": datetime.now().astimezone().isoformat(timespec="seconds"), "chances": chances, "inputs": INPUTS, "method": METHOD}
output = ROOT / "runs/replication/estimates" / (LADDER + ".json")
output.write_text(json.dumps(result, indent=2, ensure_ascii=False) + "\n")
print(json.dumps({"written": str(output), "model_mean": globals().get("mu"), "chances": chances}, indent=2))
