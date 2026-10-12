"""July observed exports, Q2 empirical Bcf/TBtu bridge, uncertain remaining months.
Only mef read output is used. Run from repository root; writes only to runs/.
"""
from datetime import datetime
import json
import math
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
RESEARCH = ROOT / 'runs/replication/research/energy'
LADDER = 'KXVG-26OCTLNGVOL'

def cite(log, url_index, locator, excerpt, claim):
    record = json.loads((RESEARCH / (log + '.json')).read_text())['read'][url_index]
    passage = next(p['text'] for p in record['passages'] if p['locator'] == locator)
    assert excerpt in passage, (locator, excerpt)
    return dict(url=record['url'], locator=locator, excerpt=excerpt, claim=claim)

pdf = json.loads((RESEARCH/'doe-july.json').read_text())['read'][0]
series = next(p['text'] for p in pdf['passages'] if p['locator']=='page-014')
# DOE last seven columns are January through July 2026; parse the two rows.
import re
cp = [float(x) for x in re.search(r'Pass\), LA\n((?:[\d.]+\s+){11}[\d.]+)',series).group(1).split()]
pq = [float(x) for x in re.search(r'Plaquemines, LA ((?:[\d.]+\s+){11}[\d.]+)',series).group(1).split()]
assert len(cp)==len(pq)==12
q2_bcf = sum(cp[-4:-1])+sum(pq[-4:-1])
july_bcf = cp[-1]+pq[-1]
q2_release = json.loads((RESEARCH/'vg-quarter.json').read_text())['read'][0]
q2_passage = next(p['text'] for p in q2_release['passages'] if p['locator']=='paragraph-0027')
q2_tbtu = float(re.search(r'sold ([\d.]+) TBtu',q2_passage).group(1))
# This empirical bridge includes heating value and any export/sales timing difference;
# it is an assumption that it persists into Q3, not a metered Q3 conversion.
bridge = q2_tbtu/q2_bcf
mean = july_bcf * (92/31) * bridge
sigma = 30.0  # Subjective TBtu SD: missing Aug/Sep, commissioning, timing/bridge error.
thresholds = next(x['thresholds'] for x in json.loads((ROOT/'runs/replication/open-q3.json').read_text())['ladders'] if x['ladder']==LADDER)
inputs = [
 cite('doe-july',0,'page-014','Cameron (Calcasieu\nPass), LA\n42.9 43.1 39.1 46.6 50.9 47.2 43.5 47.2 47.3 43.6 43.7 47.3','DOE monthly Calcasieu Pass exports in Bcf, August 2025 through July 2026; Apr/May/Jun/Jul 2026 are 47.3/43.6/43.7/47.3.'),
 cite('doe-july',0,'page-014','Plaquemines, LA 78.5 78.6 107.2 104.8 110.6 115.9 96.4 118.5 108.6 111.6 104.9 100.8','DOE monthly Plaquemines exports in the same order and Bcf units; Apr/May/Jun/Jul 2026 are 108.6/111.6/104.9/100.8.'),
 cite('doe-july',0,'page-014','U.S.-Produced LNG Exports by Point of Exit\nVolume (Bcf) 2025 2026','The monthly point-of-exit series uses volume in Bcf.'),
 cite('vg-quarter',0,'paragraph-0027','Exported 127 cargos and sold 466.4 TBtu of liquefied natural gas ("LNG")','Reported Q2 sold LNG volume is 466.4 TBtu; this calibrates the Q2 DOE-volume bridge rather than treating Bcf as TBtu.'),
 cite('vg-quarter',0,'paragraph-0002','August 11, 2026','The prior quarterly report date informs the explicitly expected November report-date assumption.'),
 cite('vg-quarter',0,'paragraph-0052','we remain on schedule to produce first LNG in the second half of 2027','CP2 is excluded from Q3 export projection because the issuer schedules its first LNG for 2027.'),
 cite('doe-refresh',0,'item-0058','Natural Gas Imports and Exports Monthly July 2026.pdf September 22, 2026','Latest DOE monthly publication found on the current index is July, released September 22.'),
 cite('vg-contract',0,'json','Will Venture Global, Inc. report Above 440 tbtu lng volumes in Q3 2026?','Venue contract title establishes TBtu threshold units and a strictly-above event.'),
]
result = {
 'ladder':LADDER,'report_date':'2026-11-10','filed_at':datetime.now().astimezone().isoformat(),
 'chances':[{'strike':s,'above':round(0.5*math.erfc((s+0.05-mean)/(sigma*math.sqrt(2))),8)} for s in thresholds],
 'inputs':inputs,
 'method':f'July DOE exports total {july_bcf:.1f} Bcf at Calcasieu Pass and Plaquemines; scaling the observed July daily rate over the 92-day quarter and multiplying by the empirical Q2 bridge ({q2_tbtu:.1f} TBtu sold / {q2_bcf:.1f} Bcf exported) gives a mean of {mean:.3f} TBtu. I model reported volume with a normal distribution and subjective 30-TBtu standard deviation for unobserved August/September, commissioning changes, and an assumed stable export-to-sales/heating-value bridge; this uncertainty is not statistically fitted, and probabilities use an assumed 0.1-TBtu reporting step to handle strict exceedance. CP2 is excluded based on its stated 2027 first-LNG timing, and no later DOE monthly observation was located on the refreshed index. The report date of 2026-11-10 is expected, not announced, using a roughly three-month interval after the August 11 Q2 release.'
}
out=ROOT/'runs/replication/estimates'/f'{LADDER}.json'
out.write_text(json.dumps(result,indent=2)+'\n')
(RESEARCH/'vg-model.json').write_text(json.dumps({'q2_bcf':q2_bcf,'july_bcf':july_bcf,'bridge_tbtu_per_bcf':bridge,'mean_tbtu':mean,'subjective_sigma_tbtu':sigma},indent=2)+'\n')
print(out.relative_to(ROOT))
