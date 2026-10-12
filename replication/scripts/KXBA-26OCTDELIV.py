"""Reproduce a cited Q3 estimate; all source acquisitions are saved under runs.
Research prototype, not investment advice. No network, credentials, or market prices.
"""
import json
import math
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
LADDER = 'KXBA-26OCTDELIV'
open_data = json.loads((ROOT / "runs/replication/open-q3.json").read_text())
thresholds = next(x["thresholds"] for x in open_data["ladders"] if x["ladder"] == LADDER)
triage = json.loads((ROOT / "runs/replication/triage.json").read_text())["triage"]
report_date = next(x.get("report_date") for x in triage if x["ladder"] == LADDER) or "2026-11-10"
INPUTS = [{'url': 'https://www.airdatanews.com/boeing-delivers-53-aircraft-in-july-bringing-2026-total-to-367/', 'locator': 'paragraph-0001', 'excerpt': 'Boeing delivered 53 commercial aircraft in July, bringing its total for the first seven months of 2026 to 367 aircraft', 'claim': 'Observed July commercial-airplane deliveries53.'}, {'url': 'https://www.marketscreener.com/news/boeing-delivers-51-planes-in-august-ce785bd8de8df627', 'locator': 'paragraph-0004', 'excerpt': 'Boeing delivered 51 airplanes and booked 15 gross orders in August, the plane maker said Tuesday.', 'claim': "Observed August deliveries51; this overrides the September tracker article's August estimate 53."}, {'url': 'https://flightplan.forecastinternational.com/2026/10/05/september-2026-commercial-aircraft-manufacturing-intelligence-production-trends-delivery-outlook/', 'locator': 'paragraph-0012', 'excerpt': 'We expect Boeing to report a slight increase to approximately 56 total deliveries, up from 53 in the previous month, led by 43 737 MAX aircraft.', 'claim': "Latest checked September delivery tracker projects56, not an issuer-certified monthly count; tracker's August53 conflicts with observed51."}]
METHOD = "Observed July 53 plus August 51 totals104; I model September as a rounded normal count with mean 56 from the October 5 delivery tracker and a subjective four-aircraft standard deviation, giving a Q3 total centered on 160. The tracker's prior-August estimate 53 differs from the issuer-reported 51, so I use the reported August count and retain forecast error rather than treating September tracking as final. For calendar Q3 commercial-airplane deliveries I compute P(total > strike) with a half-aircraft continuity correction; no issuer-certified September total was verified in the checked sources as of filing."

mu, sigma = 53 + 51 + 56, 4.0
chances = [{"strike": s, "above": round(0.5 * math.erfc((s + 0.5 - mu) / (sigma * math.sqrt(2))), 8)} for s in thresholds]
result = {"ladder": LADDER, "report_date": report_date, "filed_at": datetime.now().astimezone().isoformat(timespec="seconds"), "chances": chances, "inputs": INPUTS, "method": METHOD}
output = ROOT / "runs/replication/estimates" / (LADDER + ".json")
output.write_text(json.dumps(result, indent=2, ensure_ascii=False) + "\n")
print(json.dumps({"written": str(output), "model_mean": globals().get("mu"), "chances": chances}, indent=2))
