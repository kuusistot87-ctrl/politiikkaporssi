#!/usr/bin/env python3
"""
etsi_wikimedia_kuvat.py
-----------------------
Etsii nykyisten kansanedustajien kuvat Wikimedia Commonsista
nimen perusteella ja päivittää index.json.

Ajo: python skriptit/etsi_wikimedia_kuvat.py
"""
import json, time, re, sys
from pathlib import Path
from urllib.parse import unquote, quote

try:
    import requests
except ImportError:
    print("Asenna: pip install requests")
    sys.exit(1)

INDEX = Path("edustajat_json/index.json")
KUVAT = Path("kuvat")
KUVAT.mkdir(exist_ok=True)

with open(INDEX, encoding="utf-8") as f:
    data = json.load(f)

# Kohde: nykyiset joilla eduskunta.fi-kuva (blokattu)
kohde = [e for e in data if e.get("nykyinen") and "eduskunta.fi" in e.get("kuva", "")]
print(f"Etsitään Wikimedia-kuvat {len(kohde)} nykyiselle edustajalle...\n")

# API-haut: Wikimedia vaatii tunnistautuvan User-Agentin
api_session = requests.Session()
api_session.headers.update({"User-Agent": "Politiikkaporssi/1.0 (https://github.com/kuusistot87-ctrl/politiikkaporssi; contact@example.com)"})

# Kuvalataukset: upload.wikimedia.org vaatii selaimen näköisen headerin
dl_session = requests.Session()
dl_session.headers.update({
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
    "Referer": "https://commons.wikimedia.org/",
    "Accept": "image/webp,image/apng,image/*,*/*;q=0.8",
})

def etsi_wikimedia(nimi: str):
    """Hakee kuvan Wikimedia Commonsista henkilön nimellä."""
    # Kokeile ensin suoraan Commons-haulla
    url = (
        "https://commons.wikimedia.org/w/api.php"
        "?action=query&list=search&srsearch="
        + quote(nimi + " politician Finland")
        + "&srnamespace=6&srlimit=3&format=json"
    )
    try:
        r = api_session.get(url, timeout=10)
        results = r.json().get("query", {}).get("search", [])
        for res in results:
            title = res["title"]  # esim. "File:Pauli Aalto-Setälä.jpg"
            if any(x in title.lower() for x in [".jpg", ".jpeg", ".png", ".webp"]):
                return title
    except:
        pass
    return None

def wikimedia_kuva_url(file_title: str, leveys=300) -> str:
    """Hakee suoran kuva-URL:n tiedoston nimellä."""
    tiedosto = file_title.replace("File:", "").strip()
    return (
        "https://commons.wikimedia.org/w/index.php"
        f"?title=Special:Redirect/file/{quote(tiedosto)}&width={leveys}"
    )

def lataa_kuva(url: str, kohde_tiedosto: Path, yritykset: int = 3) -> bool:
    if kohde_tiedosto.exists() and kohde_tiedosto.stat().st_size > 1000:
        return True
    for yritys in range(yritykset):
        try:
            r = dl_session.get(url, timeout=15)
            if r.status_code == 200 and len(r.content) > 1000:
                kohde_tiedosto.write_bytes(r.content)
                return True
            elif r.status_code == 429:
                print(f" [rate limit, odotetaan...]", end="", flush=True)
                time.sleep(5 + yritys * 3)
            elif r.status_code == 403:
                time.sleep(2)
        except Exception:
            time.sleep(2)
    return False

def siisti_tiedostonimi(nimi: str) -> str:
    korvaukset = {"ä": "a", "ö": "o", "å": "a", "Ä": "A", "Ö": "O", "Å": "A"}
    s = "".join(korvaukset.get(c, c) for c in nimi)
    return re.sub(r"[^\w\-.]", "_", s) + ".jpg"

# Yritä myös suoraan Wikipedia-haulla henkilösivun kautta
def etsi_wikipedia_kuva(nimi: str):
    """Hakee kuvan suomenkielisen Wikipedia-artikkelin kautta."""
    url = (
        "https://fi.wikipedia.org/w/api.php"
        "?action=query&titles=" + quote(nimi)
        + "&prop=pageimages&pithumbsize=300&format=json"
    )
    try:
        r = api_session.get(url, timeout=10)
        pages = r.json().get("query", {}).get("pages", {})
        for page in pages.values():
            thumb = page.get("thumbnail", {}).get("source")
            if thumb:
                return thumb
    except:
        pass
    return None

# ── Pääsilmukka ────────────────────────────────────────────────────────
loydetty   = 0
ei_loydy   = 0
virhe      = 0
ei_loydy_lista = []

for i, e in enumerate(kohde):
    nimi = e["nimi"]
    # Korjaa mahdollinen encoding-ongelma nimessä
    try:
        nimi_korjattu = nimi.encode("latin-1").decode("utf-8")
    except:
        nimi_korjattu = nimi

    fn       = siisti_tiedostonimi(nimi_korjattu)
    tiedosto = KUVAT / fn

    print(f"[{i+1:3d}/{len(kohde)}] {nimi_korjattu[:35]:<35} ", end="", flush=True)

    # 1. Yritä Wikipedia (nopein)
    kuva_url = etsi_wikipedia_kuva(nimi_korjattu)

    # 2. Jos ei löydy, yritä Commons-haku
    if not kuva_url:
        file_title = etsi_wikimedia(nimi_korjattu)
        if file_title:
            kuva_url = wikimedia_kuva_url(file_title)

    if kuva_url:
        if lataa_kuva(kuva_url, tiedosto):
            e["kuva"] = f"kuvat/{fn}"
            loydetty += 1
            print(f"✓")
        else:
            # Yritä uudelleen pienen tauon jälkeen
            time.sleep(2)
            if lataa_kuva(kuva_url, tiedosto):
                e["kuva"] = f"kuvat/{fn}"
                loydetty += 1
                print(f"✓ (retry)")
            else:
                print(f"✗ (lataus epäonnistui)")
                virhe += 1
    else:
        print(f"– (ei löydy)")
        ei_loydy += 1
        ei_loydy_lista.append(nimi_korjattu)

    time.sleep(0.5)  # Pidempi viive rate limitingin välttämiseksi

# ── Tallenna ───────────────────────────────────────────────────────────
with open(INDEX, "w", encoding="utf-8") as f:
    json.dump(data, f, ensure_ascii=False, separators=(",", ":"))

print(f"\n{'─'*50}")
print(f"✓ Löydetty ja ladattu: {loydetty}")
print(f"✗ Latausvirhe:         {virhe}")
print(f"– Ei löydy:            {ei_loydy}")

if ei_loydy_lista:
    print(f"\nEi löytynyt ({len(ei_loydy_lista)} kpl):")
    for n in ei_loydy_lista:
        print(f"  {n}")

print(f"\nSeuraavaksi:")
print(f"  git add kuvat/ edustajat_json/index.json")
print(f'  git commit -m "Haetaan kansanedustajien kuvat Wikimediasta"')
print(f"  git push")
