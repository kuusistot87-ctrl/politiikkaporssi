#!/usr/bin/env python3
"""
lataa_kuvat.py - Lataa kansanedustajien kuvat paikallisesti
Vaatii: pip install requests
Aja: python lataa_kuvat.py
"""
import json, time, re, sys
from pathlib import Path

try:
    import requests
except ImportError:
    print("Asenna requests: pip install requests")
    sys.exit(1)

INDEX = Path("edustajat_json/index.json")
KUVAT = Path("kuvat")
KUVAT.mkdir(exist_ok=True)

with open(INDEX, encoding="utf-8") as f:
    data = json.load(f)

nykyiset = [e for e in data if e.get("nykyinen") and e.get("kuva","").startswith("http")]
print(f"Ladataan {len(nykyiset)} kuvaa...\n")

# Käytä session joka pitää cookiet
session = requests.Session()
session.headers.update({
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
    "Accept": "image/avif,image/webp,image/apng,image/svg+xml,image/*,*/*;q=0.8",
    "Accept-Language": "fi-FI,fi;q=0.9,en;q=0.8",
    "Referer": "https://www.eduskunta.fi/FI/kansanedustajat/nykyiset_kansanedustajat/Sivut/default.aspx",
    "sec-ch-ua": '"Chromium";v="122", "Not(A:Brand";v="24"',
    "sec-fetch-dest": "image",
    "sec-fetch-mode": "no-cors",
    "sec-fetch-site": "same-origin",
})

# Käy ensin etusivulla hakemassa cookiet
try:
    session.get("https://www.eduskunta.fi/FI/kansanedustajat/Sivut/default.aspx", timeout=10)
except:
    pass

ladattu = 0
virhe   = 0

for i, e in enumerate(nykyiset):
    kuva_url = e["kuva"]
    m = re.search(r'-web-(\d+)\.jpg', kuva_url)
    if not m:
        virhe += 1; continue

    pid      = m.group(1)
    tiedosto = KUVAT / f"{pid}.jpg"

    if tiedosto.exists() and tiedosto.stat().st_size > 1000:
        e["kuva"] = f"kuvat/{pid}.jpg"
        ladattu += 1
        continue

    try:
        r = session.get(kuva_url, timeout=10)
        if r.status_code == 200 and len(r.content) > 1000:
            tiedosto.write_bytes(r.content)
            e["kuva"] = f"kuvat/{pid}.jpg"
            ladattu += 1
            if ladattu % 20 == 0 or ladattu <= 3:
                print(f"  [{ladattu}] ✓ {e['nimi']}")
        else:
            print(f"  ✗ {e['nimi']}: HTTP {r.status_code}, {len(r.content)} bytes")
            virhe += 1
        time.sleep(0.3)
    except Exception as ex:
        print(f"  ✗ {e['nimi']}: {ex}")
        virhe += 1

with open(INDEX, "w", encoding="utf-8") as f:
    json.dump(data, f, ensure_ascii=False, separators=(",",":"))

print(f"\nValmis! Ladattu: {ladattu}, Virheitä: {virhe}")
print(f"Kansio: kuvat/ ({sum(1 for _ in KUVAT.glob('*.jpg'))} tiedostoa)")
