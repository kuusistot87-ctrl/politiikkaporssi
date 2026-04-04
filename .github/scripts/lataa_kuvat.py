#!/usr/bin/env python3
"""
lataa_kuvat.py - Lataa kansanedustajien kuvat paikallisesti
Käsittelee sekä eduskunta.fi- että Wikimedia Commons -kuvat.
Vaatii: pip install requests
Aja projektijuuresta: python skriptit/lataa_kuvat.py
"""
import json, time, re, sys
from pathlib import Path
from urllib.parse import unquote

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

kaikki = [e for e in data if e.get("kuva", "").startswith("http")]
print(f"Ladataan {len(kaikki)} kuvaa (eduskunta.fi + Wikimedia)...\n")

# ── Session ────────────────────────────────────────────────────────────
session = requests.Session()
session.headers.update({
    "User-Agent": "Politiikkaporssi/1.0 (https://github.com/kuusistot87-ctrl/politiikkaporssi; contact@example.com)",
    "Accept": "image/avif,image/webp,image/apng,image/svg+xml,image/*,*/*;q=0.8",
    "Accept-Language": "fi-FI,fi;q=0.9,en;q=0.8",
    "Referer": "https://www.eduskunta.fi/FI/kansanedustajat/nykyiset_kansanedustajat/Sivut/default.aspx",
    "sec-fetch-dest": "image",
    "sec-fetch-mode": "no-cors",
    "sec-fetch-site": "same-origin",
})

try:
    session.get("https://www.eduskunta.fi/FI/kansanedustajat/Sivut/default.aspx", timeout=10)
    print("  Cookie haettu eduskunta.fi:stä\n")
except:
    print("  Varoitus: eduskunta.fi ei vastannut cookie-haussa\n")

# ── Apufunktiot ────────────────────────────────────────────────────────

def tiedostonimi_eduskunta(url):
    """Palauttaa tiedostonimen eduskunta.fi-URL:sta, esim. 'Aalto-Setala-Pauli-web-1504.jpg'"""
    m = re.search(r'/PublishingImages/(.+\.jpg)', url, re.IGNORECASE)
    return m.group(1) if m else None

def wikimedia_dl_url(url, leveys=300):
    """Muuntaa Special:FilePath → ladattavaksi URL:ksi"""
    if "Special:FilePath" in url:
        tiedosto = re.sub(r"^.*Special:FilePath/", "", url)
        return (
            "https://commons.wikimedia.org/w/index.php"
            f"?title=Special:Redirect/file/{tiedosto}&width={leveys}"
        )
    return url

def tiedostonimi_wikimedia(url):
    """Palauttaa siistin tiedostonimen Wikimedia-URL:sta"""
    tiedosto = re.sub(r"^.*Special:FilePath/", "", url)
    tiedosto = unquote(tiedosto)
    tiedosto = re.sub(r'[<>:"/\\|?*]', '_', tiedosto)
    if not re.search(r'\.(jpg|jpeg|png|webp)$', tiedosto, re.IGNORECASE):
        tiedosto += ".jpg"
    return tiedosto

# ── Pääsilmukka ────────────────────────────────────────────────────────

ladattu_edu  = 0
ladattu_wiki = 0
ohitettu     = 0
virhe        = 0

for i, e in enumerate(kaikki):
    kuva_url = e["kuva"]
    nimi     = e.get("nimi", f"#{i}")

    # ── EDUSKUNTA.FI ──────────────────────────────────────────────────
    if "eduskunta.fi" in kuva_url:
        fn = tiedostonimi_eduskunta(kuva_url)
        if not fn:
            print(f"  ✗ {nimi}: ei tunnistettu eduskunta-URL")
            virhe += 1
            continue

        tiedosto = KUVAT / fn
        if tiedosto.exists() and tiedosto.stat().st_size > 1000:
            e["kuva"] = f"kuvat/{fn}"
            ohitettu += 1
            continue

        try:
            r = session.get(kuva_url, timeout=10)
            if r.status_code == 200 and len(r.content) > 1000:
                tiedosto.write_bytes(r.content)
                e["kuva"] = f"kuvat/{fn}"
                ladattu_edu += 1
                if (ladattu_edu + ladattu_wiki) % 20 == 0 or ladattu_edu <= 3:
                    print(f"  [{i+1}] ✓ (edu) {nimi}")
            else:
                print(f"  ✗ {nimi}: HTTP {r.status_code} — eduskunta.fi ehkä alas")
                virhe += 1
            time.sleep(0.3)
        except Exception as ex:
            print(f"  ✗ {nimi}: {ex}")
            virhe += 1

    # ── WIKIMEDIA COMMONS ─────────────────────────────────────────────
    elif "wikimedia.org" in kuva_url or "wikipedia.org" in kuva_url or "Special:FilePath" in kuva_url:
        fn       = tiedostonimi_wikimedia(kuva_url)
        dl_url   = wikimedia_dl_url(kuva_url, leveys=300)
        tiedosto = KUVAT / fn

        if tiedosto.exists() and tiedosto.stat().st_size > 1000:
            e["kuva"] = f"kuvat/{fn}"
            ohitettu += 1
            continue

        try:
            r = session.get(dl_url, timeout=15)
            if r.status_code == 200 and len(r.content) > 1000:
                tiedosto.write_bytes(r.content)
                e["kuva"] = f"kuvat/{fn}"
                ladattu_wiki += 1
                if (ladattu_edu + ladattu_wiki) % 50 == 0 or ladattu_wiki <= 3:
                    print(f"  [{i+1}] ✓ (wiki) {nimi}")
            else:
                print(f"  ✗ {nimi}: HTTP {r.status_code}")
                virhe += 1
            time.sleep(0.2)
        except Exception as ex:
            print(f"  ✗ {nimi}: {ex}")
            virhe += 1

    else:
        ohitettu += 1

# ── Tallenna index.json ────────────────────────────────────────────────
with open(INDEX, "w", encoding="utf-8") as f:
    json.dump(data, f, ensure_ascii=False, separators=(",", ":"))

print(f"\n{'─'*50}")
print(f"✓ Ladattu eduskunta.fi:   {ladattu_edu}")
print(f"✓ Ladattu Wikimedia:      {ladattu_wiki}")
print(f"– Ohitettu (jo olemassa): {ohitettu}")
print(f"✗ Virheitä:               {virhe}")
print(f"\nKansio kuvat/: {sum(1 for _ in KUVAT.glob('*'))} tiedostoa")
print(f"\nSeuraavaksi:")
print(f"  git add kuvat/ edustajat_json/index.json")
print(f'  git commit -m "Lisätään kansanedustajien kuvat paikallisesti"')
print(f"  git push")
