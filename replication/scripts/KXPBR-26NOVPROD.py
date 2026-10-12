"""Reproduce an empirical regulator-to-company production bridge from saved mef-read passages.

This is a research prototype. The ANP concessionaire series is not asserted to be
Petrobras's own quarterly definition. The Q2 additive bridge absorbs rather than
identifies differences in scope, gas/CO2/reinjection treatment and geographic coverage.
A single-quarter calibration does not estimate model reliability. No keys or network.
"""
import json
import math
import re
from pathlib import Path
from datetime import datetime, timezone
ROOT = Path(__file__).resolve().parents[3]
RESEARCH = ROOT / 'runs/replication/research/pbr'
LADDER = 'KXPBR-26NOVPROD'
reads = json.loads((RESEARCH / 'anp-months.json').read_text())['read']
inputs = []
values = {}
oil_values = {}
def normalized(x):
    return re.sub(r'\s+', ' ', x).strip()
def citation(filename, fragment, locator, excerpt, claim):
    records = json.loads((RESEARCH / filename).read_text())['read']
    rec = next(r for r in records if fragment in r['url'])
    passage = next(p['text'] for p in rec['passages'] if p['locator'] == locator)
    assert normalized(excerpt) in normalized(passage)
    return dict(url=rec['url'], locator=locator, excerpt=excerpt, claim=claim)
def number_pt(s):
    return float(s.replace('.', '').replace(',', '.'))
for month in ['abril','maio','junho','julho','agosto']:
    rec = next(r for r in reads if '/' + month + '.pdf' in r['url'])
    text = next(p['text'] for p in rec['passages'] if p['locator'] == 'page-015')
    row = re.search(r'PETROBRAS\s+([\d.,]+)\s+([\d.,]+)\s+([\d.,]+)', text)
    assert row is not None
    oil, gas, total = [number_pt(t) for t in row.groups()]
    values[month] = total / 1000  # boe/d -> Mboed (thousand boe/day)
    oil_values[month] = oil / 1000
    # Regulator provides its own boe total: no external gas conversion is invented.
    excerpt = text[text.index('Produção de petróleo e gás por consorciado'):row.end()]
    inputs.append(dict(url=rec['url'], locator='page-015', excerpt=excerpt,
                       claim=f'{month.capitalize()} 2026 Petrobras concessionaire production: oil {oil:,.2f} b/d, gas {gas:,.2f} thousand m3/d, and total {total:,.2f} boe/d, using the regulator\'s own gas-to-boe conversion.'))
inputs.append(citation('anp-months.json','/agosto.pdf','page-004',
    'Na tabela “Distribuição da produção de petróleo e gás natural por consorciado”, a Pré-Sal Petróleo \nS.A. (PPSA) representa o volume de petróleo e gás natural apropriado à União conforme contratos de \npartilha da produção. Tal volume não é contabilizado nos valores atribuídos aos demais contratados, \nnestes casos.',
    'ANP concessionaire allocation excludes the government share attributed to PPSA from the other contractors\' volumes.'))
inputs.append(citation('baseline.json','petrobras-q2-profit','paragraph-0004',
    "Petrobras' own oil output in Brazil reached 2.7 million barrels per day, 15% above the second quarter of 2025. Total oil and natural gas production reached a record 3.34 million barrels of oil equivalent per day, while operated production hit 4.87 million boed.",
    'Read secondary report of the Q2 2026 company production baseline distinguishes own oil, total oil/gas and operated production; own-oil counts do not match the ANP Q2 concessionaire average exactly.'))
inputs.append(citation('baseline.json','theglobeandmail','paragraph-0007',
    'In the second quarter of 2026, Petrobras reported record total oil and natural gas production of 3.34 MMboed',
    'Independent read secondary summary corroborates the Q2 2026 total production baseline and its million-boe/day units; this is not a primary issuer definition.'))
inputs.append(citation('anp-check.json','boletim-mensal','paragraph-0004',
    'Janeiro - Fevereiro - Março - Abril - Maio - Junho - Julho - Agosto',
    'The refreshed 2026 regulator bulletin index lists January through August, with no September observation verified.'))
# Calendar-day weighted quarter-average rates. Missing September persists August's rate.
q2_anp = (30*values['abril'] + 31*values['maio'] + 30*values['junho']) / 91
q2_company = 3340.0  # 3.34 million boe/d, two cited secondary reports.
bridge_gap = q2_company - q2_anp
september = values['agosto']
q3_anp = (31*values['julho'] + 31*values['agosto'] + 30*september) / 92
mean = q3_anp + bridge_gap
sd = 150.0  # Subjective total model SD; not fitted from one quarterly calibration.
# Assume reporting rounds nearest 1 Mboed; strict-above a lattice strike uses +0.5.
def probability(strike):
    return 0.5 * math.erfc((strike + 0.5 - mean)/(sd*math.sqrt(2)))
thresholds = next(r['thresholds'] for r in json.loads((ROOT/'runs/replication/open-q3.json').read_text())['ladders'] if r['ladder'] == LADDER)
method = (
    f'Use the ANP concessionaire series, whose totals already convert gas to boe and exclude the PPSA government share, to form a day-weighted Q2 rate of {q2_anp:.6f} Mboed and calibrate an additive gap of {bridge_gap:.6f} Mboed to the 3,340 Mboed company total reported in two read secondary summaries; day-weight July and August plus assumed September persistence at August to project Q3 at {mean:.6f} Mboed. '
    'Assume this additive bridge remains stable and use a normal latent quarter-average rate with a subjective 150 Mboed standard deviation, not a fitted confidence interval, covering the missing month, preliminary/source uncertainty and unidentified gas/reinjection/CO2, ownership and overseas scope differences; the reported own-Brazil-oil baseline also differs from the ANP concessionaire Q2 average, so the series are not treated as identical metrics. '
    'Assume quarterly reporting rounds to the nearest 1 Mboed and compute strictly-above chances from each strike plus 0.5 Mboed, with the rounded Q2 baseline uncertainty absorbed in the subjective standard deviation. '
    'November 6, 2026 is an unverified expected report date used only as a scheduling assumption; the refreshed ANP 2026 index ends at August and checked searches supplied no September numeric observation.'
)
output = dict(ladder=LADDER, report_date='2026-11-06',filed_at=datetime.now(timezone.utc).isoformat(),
              chances=[dict(strike=s,above=round(probability(s),8)) for s in thresholds],inputs=inputs,method=method)
assert all(a['above']>=b['above'] for a,b in zip(output['chances'],output['chances'][1:]))
path=ROOT/'runs/replication/estimates'/f'{LADDER}.json'
path.write_text(json.dumps(output,indent=2)+'\n')
print(json.dumps(dict(file=str(path),filed_at=output['filed_at'],anp_Mboed=values,q2_anp=q2_anp,bridge_gap=bridge_gap,q3_anp=q3_anp,mean=mean,sd=sd,anp_q2_oil_Mbpd=(30*oil_values['abril']+31*oil_values['maio']+30*oil_values['junho'])/91,chances=output['chances']),indent=2))
