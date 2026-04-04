#!/usr/bin/env python3
"""
nimeä_aanestykset.py
--------------------
Nimeää äänestys-JSON:t skandinimistä ASCII-muotoon
JA kopioi datan tyhjiin ASCII-tiedostoihin jos vanha skandiversio on täynnä.

Ajo: python skriptit/nimeä_aanestykset.py
"""
import json, re, shutil
from pathlib import Path

KANSIO = Path("aanestykset_json")

def ascii_slug(nimi):
    korvaukset = {'ä':'a','ö':'o','å':'a','Ä':'A','Ö':'O','Å':'A'}
    s = ''.join(korvaukset.get(c, c) for c in nimi)
    return s.replace(' ', '_')

tiedostot = list(KANSIO.glob("*.json"))
print(f"Löydettiin {len(tiedostot)} tiedostoa\n")

# Ryhmittele tiedostot nimen mukaan
nimien_tiedostot = {}
for t in tiedostot:
    if t.stem == '_meta':
        continue
    try:
        with open(t, encoding='utf-8') as f:
            data = json.load(f)
        nimi = data.get('nimi', '')
        if not nimi:
            continue
        slug = ascii_slug(nimi)
        if slug not in nimien_tiedostot:
            nimien_tiedostot[slug] = []
        nimien_tiedostot[slug].append((t, data, len(data.get('aanestykset', []))))
    except:
        pass

korjattu = 0
poistettu = 0

for slug, versiot in nimien_tiedostot.items():
    ascii_polku = KANSIO / f"{slug}.json"
    
    # Järjestä: eniten äänestyksiä ensin
    versiot.sort(key=lambda x: x[2], reverse=True)
    paras = versiot[0]
    
    if paras[2] == 0:
        # Kaikki tyhjiä — ei tehdä mitään
        continue
    
    # Tallenna paras data ASCII-nimellä
    with open(ascii_polku, 'w', encoding='utf-8') as f:
        json.dump(paras[1], f, ensure_ascii=False, separators=(',',':'))
    korjattu += 1
    
    # Poista muut versiot (skandiversiot)
    for t, _, _ in versiot:
        if t != ascii_polku and t.exists():
            t.unlink()
            poistettu += 1
    
    print(f"✓ {slug} ({paras[2]} äänestystä)")

print(f"\n{'─'*50}")
print(f"✓ Korjattu: {korjattu}")
print(f"✗ Poistettu duplikaatit: {poistettu}")
print(f"\nSeuraavaksi:")
print(f"  git add aanestykset_json/")
print(f'  git commit -m "Korjataan äänestysdata: ASCII-nimet, poistetaan duplikaatit"')
print(f"  git push")
