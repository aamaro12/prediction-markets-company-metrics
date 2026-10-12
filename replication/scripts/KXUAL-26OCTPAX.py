"""July-measured carrier proxy projected to the reported UAL passenger perimeter.
Read source acquisition/provenance in research/airlines/README.md.
"""
from datetime import datetime, timezone
from pathlib import Path
import json
import math
rep=Path(__file__).resolve().parents[1]
research=rep/'research'/'airlines'
ladder='KXUAL-26OCTPAX'
bts='https://www.transtats.bts.gov/carriers.asp?mef_form_post=1&Carrier=UA&End_YearMonth=24319'
issuer='https://www.prnewswire.com/news-releases/united-airlines-continues-to-win-brand-loyal-customers-as-q3-profit-and-q4-outlook-both-exceed-wall-street-expectations-302585413.html'
inputs=[
 {'url':bts,'locator':'table-003','excerpt':'United Air Lines (UA) Scheduled Services Only BTS Data as of 10/12/2026','claim':'Selected UA operating-carrier scheduled-services proxy, acquired via visible public POST form.'},
 {'url':issuer,'locator':'table-003','excerpt':'Three Months Ended September 30, % Increase/ (Decrease) Nine Months Ended September 30, % Increase/ (Decrease) 2025 2024 2025 2024','claim':'Prior-period operating-statistics column order: Q3 2025 then Q3 2024.'},
 {'url':issuer,'locator':'table-003','excerpt':'Passengers (thousands) (a) 48,382 45,559 6.2 135,374 129,259 4.7','claim':'Issuer reported Q3 2025 passenger total48,382,000 and comparative Q3 2024 total45,559,000, rather than certificate-only traffic.'},
 {'url':issuer,'locator':'table-004','excerpt':'(a) The number of revenue passengers measured by each flight segment flown.','claim':'Issuer target counts revenue passengers by flight segment, not unique people or seats.'},
 {'url':'https://www.transtats.bts.gov/Fields.asp?gnoyr_VQ=FIM','locator':'table-006/row-007/cell-002','excerpt':'Non-Stop Segment Passengers Transported','claim':'BTS segment passenger measure aligns conceptually with the issuer segment count, subject to revenue/nonrevenue and reporting perimeter differences.'},
 {'url':'https://www.transtats.bts.gov/Fields.asp?gnoyr_VQ=FIM','locator':'table-006/row-016/cell-002','excerpt':'A unique airline (carrier) is defined as one holding and reporting under the same DOT certificate regardless of its Code, Name, or holding company/corporation.','claim':'A certificate is not automatically the contract company/group, so use a historical reporting bridge rather than asserting equality.'},
 {'url':'https://www.transtats.bts.gov/ReleaseInfo.asp','locator':'table-001/row-005/cell-003','excerpt':'10/9/2026: 7/2026 added 4/2026 updated','claim':'July is the latest released T-100 domestic-segment month; no current August/September measurement is claimed.'},
]
for year,month,value in [(2026,'July',10768),(2025,'July',10145),(2025,'August',9722),(2025,'September',9195),(2024,'July',9483),(2024,'August',9331),(2024,'September',8633)]:
 inputs.append({'url':bts,'locator':'table-001','excerpt':f'Date: {month} {year}; Number of Passengers: {value}','claim':f'UA {month} {year} passenger chart measurement; used as a dimensionless same-carrier growth proxy and for historical bridge comparison.'})
reads=[]
for name in ['bts-selected-carriers.json','united-prior-quarter.json','united-definition.json','bts-definitions.json']:
 reads.extend(json.loads((research/name).read_text())['read'])
for c in inputs:
 assert any(r['url']==c['url'] and any(p['locator']==c['locator'] and c['excerpt'] in p['text'] for p in r.get('passages',[])) for r in reads),c
mean=48_382_000*10_768/10_145
sd=1_800_000.0
bridge_2025=48_382/(10_145+9_722+9_195)
bridge_2024=45_559/(9_483+9_331+8_633)
thresholds=next(x['thresholds'] for x in json.loads((rep/'open-q3.json').read_text())['ladders'] if x['ladder']==ladder)
report_date=next(x['report_date'] for x in json.loads((rep/'triage.json').read_text())['triage'] if x['ladder']==ladder)
method=(
 f"Project the issuer's Q3 2025 reported segment-revenue-passenger total48,382,000 by the latest in-quarter UA July passenger ratio10,768/10,145 to obtain a Q3 2026 mean of {mean:,.0f} passengers. "
 f"The certificate-only BTS chart Q3 sums29,062 in 2025 and27,447 in 2024 map to issuer totals48,382 and45,559 thousand with historical bridge factors{bridge_2025:.5f} and{bridge_2024:.5f}; preserving that bridge anchors the forecast to the contract's issuer perimeter while avoiding direct summation of regional certificates that may serve several groups. "
 "Assume a Normal predictive distribution with this mean and judgemental SD1,800,000 passengers for missing August/September observations, regional/group mix, revenue-passenger definition differences, and changes in the reporting bridge; July is the latest released month and the SD is deliberately not claimed as empirically estimated. "
 "For each strictly-above threshold, use the Normal survival probability at strike plus500 passengers as a continuity correction for the issuer's thousand-passenger reporting grid."
)
# Plain spacing in human-readable claims/method.
for item in inputs:
 item['claim']=item['claim'].replace('total48','total 48').replace('total45','total 45')
for old,new in [('total48','total 48'),('ratio10','ratio 10'),('sums29','sums 29'),('and27','and 27'),('totals48','totals 48'),('and45','and 45'),('factors1','factors 1'),('SD1','SD 1'),('plus500','plus 500')]:method=method.replace(old,new)
out={'ladder':ladder,'report_date':report_date,'filed_at':datetime.now(timezone.utc).isoformat(),'chances':[{'strike':s,'above':round(0.5*math.erfc((s+500-mean)/(sd*math.sqrt(2))),8)} for s in thresholds],'inputs':inputs,'method':method}
(rep/'estimates'/f'{ladder}.json').write_text(json.dumps(out,indent=2)+'\n')
print(json.dumps({'ladder':ladder,'mean':mean,'sd':sd,'bridge_2025':bridge_2025,'bridge_2024':bridge_2024,'thresholds':len(thresholds)}))
