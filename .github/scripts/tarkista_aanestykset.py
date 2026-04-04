import json, glob, os

tiedostot = [f for f in glob.glob('aanestykset_json/*.json') if 'index' not in f]

uusin = ''
vanhin = '9999'
tyhja = 0
yhteensa = 0

for f in tiedostot:
    with open(f, encoding='utf-8') as fh:
        d = json.load(fh)
    aanestykset = d.get('aanestykset', [])
    if not aanestykset:
        tyhja += 1
        print(f'  TYHJÄ: {os.path.basename(f)}')
        continue
    yhteensa += len(aanestykset)
    for a in aanestykset:
        pvm = a.get('pvm','')[:10]
        if pvm > uusin: uusin = pvm
        if pvm < vanhin and pvm: vanhin = pvm

print(f'Tiedostoja:      {len(tiedostot)}')
print(f'Tyhjiä:          {tyhja}')
print(f'Äänestyksiä yht: {yhteensa}')
print(f'Vanhin pvm:      {vanhin}')
print(f'Uusin pvm:       {uusin}')
print(f'Keskim. per hlö: {yhteensa // (len(tiedostot) - tyhja)}')
