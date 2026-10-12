"""Reproduce the July-measured Q3 projection; all evidence came through mef read.

BTS carrier-form acquisition command and transport provenance are recorded in
research/airlines/README.md. Only saved, listed mef passages are model inputs.
"""
from datetime import datetime, timezone
from pathlib import Path
import json
import math

rep = Path(__file__).resolve().parents[1]
research = rep / 'research' / 'airlines'
ladder = 'KXLUV-26OCTSEATS'
bts = 'https://www.transtats.bts.gov/carriers.asp?mef_form_post=1&Carrier=WN&End_YearMonth=24319'
issuer = 'https://investors.southwest.com/news-events/press-releases/detail/1901/southwest-airlines-reports-record-third-quarter-revenue-strong-execution-of-transformational-initiatives-continues'
release = 'https://www.transtats.bts.gov/ReleaseInfo.asp'
inputs = [
    {'url': bts, 'locator': 'table-003', 'excerpt': 'Southwest Airlines (WN) Scheduled Services Only BTS Data as of 10/12/2026', 'claim': 'Selected BTS WN operating carrier, scheduled services; acquired through the public POST form, not an ignored GET carrier selection.'},
    {'url': bts, 'locator': 'table-001', 'excerpt': 'Date: July 2026; Number of Seats: 19959', 'claim': 'Latest in-quarter July 2026 WN available-seat chart measurement; use its ratio to July 2025 without assuming chart units match the issuer units.'},
    {'url': bts, 'locator': 'table-001', 'excerpt': 'Date: July 2025; Number of Seats: 20149', 'claim': 'Same-carrier July 2025 denominator for current-quarter capacity growth.'},
    {'url': bts, 'locator': 'table-001', 'excerpt': 'Date: August 2025; Number of Seats: 18491', 'claim': 'Historical August WN chart available seats for baseline bridge.'},
    {'url': bts, 'locator': 'table-001', 'excerpt': 'Date: September 2025; Number of Seats: 17831', 'claim': 'Historical September WN chart available seats for baseline bridge.'},
    {'url': bts, 'locator': 'table-001', 'excerpt': 'Date: July 2024; Number of Seats: 20305', 'claim': 'Historical July WN chart available seats for baseline bridge stability check.'},
    {'url': bts, 'locator': 'table-001', 'excerpt': 'Date: August 2024; Number of Seats: 18751', 'claim': 'Historical August WN chart available seats for baseline bridge stability check.'},
    {'url': bts, 'locator': 'table-001', 'excerpt': 'Date: September 2024; Number of Seats: 17888', 'claim': 'Historical September WN chart available seats for baseline bridge stability check.'},
    {'url': issuer, 'locator': 'table-007', 'excerpt': 'Three months ended Nine months ended September 30, Percent September 30, Percent 2025 2024 Change 2025 2024 Change', 'claim': 'Operating-statistics table period and year column order.'},
    {'url': issuer, 'locator': 'table-007', 'excerpt': 'Seats flown (000s) (d) 57,643 58,119 (0.8) 170,145 173,588 (2.0)', 'claim': 'Issuer Q3 2025 seats flown 57,643,000; Q3 2024 seats flown 58,119,000, distinct from ASMs and passengers.'},
    {'url': issuer, 'locator': 'paragraph-0949', 'excerpt': '(d) Seats flown is calculated using total number of seats available by aircraft type multiplied by the total trips flown by the same aircraft type during a particular period.', 'claim': 'Target definition uses seats multiplied by trips; this is seats flown, not seat miles or passengers.'},
    {'url': bts, 'locator': 'table-004/row-001/cell-001', 'excerpt': 'Summary Data (U.S. Airports, 12 Months Ending July)', 'claim': 'BTS carrier page identifies U.S.-airport summary coverage; prior-year calibration bridges the available-seat proxy to issuer-wide reporting instead of assuming equality.'},
    {'url': release, 'locator': 'table-001/row-005/cell-003', 'excerpt': '10/9/2026: 7/2026 added 4/2026 updated', 'claim': 'July is the latest released BTS T-100 domestic segment month as of this run; no August/September observation is asserted.'},
]
# Every quoted input must appear in a saved mef read listed passage, not in raw HTML.
reads = []
for name in ['southwest-final-inputs.json','southwest-operating-tables.json','bts-southwest-units.json','bts-definitions.json']:
    reads.extend(json.loads((research/name).read_text())['read'])
for c in inputs:
    assert any(r['url']==c['url'] and any(p['locator']==c['locator'] and c['excerpt'] in p['text'] for p in r.get('passages',[])) for r in reads), c
mean = 57_643_000 * 19_959 / 20_149
sd = 1_000_000.0  # explicit conservative judgement, not claimed empirical calibration
bridge_2025 = 57_643 / (20_149+18_491+17_831)
bridge_2024 = 58_119 / (20_305+18_751+17_888)
thresholds = next(x['thresholds'] for x in json.loads((rep/'open-q3.json').read_text())['ladders'] if x['ladder']==ladder)
report_date = next(x['report_date'] for x in json.loads((rep/'triage.json').read_text())['triage'] if x['ladder']==ladder)
method = (
    f"Multiply the issuer's Q3 2025 seats flown of 57,643,000 by the latest in-quarter BTS WN July available-seat ratio 19,959/20,149 to project {mean:,.0f} seats for Q3 2026. "
    f"The BTS chart Q3 totals are 56,471 in 2025 and 56,944 in 2024, versus issuer seats flown of 57,643 and 58,119 thousand, giving stable historical bridge factors {bridge_2025:.5f} and {bridge_2024:.5f}; anchoring on the issuer baseline preserves this carrier/perimeter difference rather than treating the BTS chart as the reported figure. "
    "Use a Normal predictive distribution with this mean and judgemental SD 1,000,000 seats to allow for unobserved August/September capacity growth, reporting coverage, and changes in the bridge; July is the latest released month and this SD is not presented as empirically estimated. "
    "Because the issuer reports seats in thousands and contracts require strictly above, calculate each chance as the Normal survival probability at strike plus 500 seats, using a continuity correction for the reported rounding grid."
)
out={'ladder':ladder,'report_date':report_date,'filed_at':datetime.now(timezone.utc).isoformat(),'chances':[{'strike':s,'above':round(0.5*math.erfc((s+500-mean)/(sd*math.sqrt(2))),8)} for s in thresholds],'inputs':inputs,'method':method}
(rep/'estimates'/f'{ladder}.json').write_text(json.dumps(out,indent=2)+'\n')
print(json.dumps({'ladder':ladder,'mean':mean,'sd':sd,'bridge_2025':bridge_2025,'bridge_2024':bridge_2024,'thresholds':len(thresholds)}))
