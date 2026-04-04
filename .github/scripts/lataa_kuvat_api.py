#!/usr/bin/env python3
"""
lataa_kuvat_api.py
------------------
Lataa kaikki 200 nykyisen kansanedustajan kuvat
eduskunnan uudesta API:sta: /api/memberImages/{pid}
Ajo: python skriptit/lataa_kuvat_api.py
"""
import json, re, time
from pathlib import Path

try:
    import requests
except ImportError:
    import sys; print("pip install requests"); sys.exit(1)

INDEX     = Path("edustajat_json/index.json")
KUVAT_DIR = Path("kuvat")
KUVAT_DIR.mkdir(exist_ok=True)

with open(INDEX, encoding="utf-8") as f:
    data = json.load(f)

nykyiset = [e for e in data if e.get("nykyinen")]
print(f"Ladataan {len(nykyiset)} nykyisen edustajan kuvat eduskunnan API:sta...\n")

dl = requests.Session()
dl.headers.update({
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
    "Referer": "https://www.eduskunta.fi/",
    "Accept": "image/webp,image/apng,image/*,*/*;q=0.8",
})

def hae_pid(eduskunta_url):
    m = re.search(r"/(\d+)\.aspx", eduskunta_url or "")
    return m.group(1) if m else None

ladattu = 0
virhe   = 0
ei_pid  = 0

for i, e in enumerate(nykyiset):
    nimi = e.get("nimi", f"#{i}")
    try:
        nimi = nimi.encode("latin-1").decode("utf-8")
    except:
        pass

    pid = hae_pid(e.get("eduskunta", ""))
    if not pid:
        print(f"[{i+1:3d}/200] {nimi[:35]:<35} – ei PID")
        ei_pid += 1
        continue

    kohde = KUVAT_DIR / f"{pid}.jpg"
    print(f"[{i+1:3d}/200] {nimi[:35]:<35} ", end="", flush=True)

    # Ohita jos jo ladattu ja iso tiedosto
    if kohde.exists() and kohde.stat().st_size > 10000:
        # Päivitä index.json osoittamaan tähän
        e["kuva"] = f"kuvat/{pid}.jpg"
        ladattu += 1
        print(f"✓ (ohitettu, jo olemassa)")
        continue

    try:
        url = f"https://www.eduskunta.fi/api/memberImages/{pid}"
        r = dl.get(url, timeout=15)
        if r.status_code == 200 and len(r.content) > 5000:
            kohde.write_bytes(r.content)
            e["kuva"] = f"kuvat/{pid}.jpg"
            ladattu += 1
            print(f"✓ ({len(r.content)//1024}KB)")
        elif r.status_code == 429:
            print(f"[rate limit] ", end="", flush=True)
            time.sleep(5)
            r = dl.get(url, timeout=15)
            if r.status_code == 200 and len(r.content) > 5000:
                kohde.write_bytes(r.content)
                e["kuva"] = f"kuvat/{pid}.jpg"
                ladattu += 1
                print(f"✓ retry ({len(r.content)//1024}KB)")
            else:
                print(f"✗ HTTP {r.status_code}")
                virhe += 1
        else:
            print(f"✗ HTTP {r.status_code} ({len(r.content)} bytes)")
            virhe += 1
        time.sleep(0.3)
    except Exception as ex:
        print(f"✗ {ex}")
        virhe += 1

# Tallenna index.json
with open(INDEX, "w", encoding="utf-8") as f:
    json.dump(data, f, ensure_ascii=False, separators=(",", ":"))

print(f"\n{'─'*50}")
print(f"✓ Ladattu:    {ladattu}")
print(f"✗ Virheitä:   {virhe}")
print(f"– Ei PID:     {ei_pid}")
print(f"\nSeuraavaksi:")
print(f"  git add kuvat/ edustajat_json/index.json")
print(f'  git commit -m "Päivitetään kuvat eduskunnan uudesta API:sta"')
print(f"  git push")
