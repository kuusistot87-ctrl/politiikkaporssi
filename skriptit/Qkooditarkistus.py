python -c "
import json
from pathlib import Path
from collections import Counter

def kentta_id(data, avain):
    v = data.get(avain)
    if not v: return ''
    if isinstance(v, list): v = v[-1]
    return v.get('@id','') if isinstance(v,dict) else ''

qids = Counter()
for f in Path('edustajat_json').glob('*.json'):
    if f.name == 'index.json': continue
    try:
        d = json.loads(f.read_text(encoding='utf-8'))
        qid = kentta_id(d, 'semparl:party').split(':')[-1]
        if qid: qids[qid] += 1
    except: pass

for q,n in sorted(qids.items(), key=lambda x:-x[1])[:30]:
    print(f'{q:15s} {n}')
"