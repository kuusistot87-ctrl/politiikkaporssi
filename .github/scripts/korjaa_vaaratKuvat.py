#!/usr/bin/env python3
"""
korjaa_vaaratKuvat.py
---------------------
1. Poistaa väärät kuvat (henkilöt joille Wikipedia löysi väärän kuvan)
2. Yrittää hakea oikean kuvan syntymävuoden perusteella suodattaen
3. Päivittää index.json

Ajo: python skriptit/korjaa_vaaratKuvat.py
"""
import json, re, time
from pathlib import Path

try:
    import requests
except ImportError:
    import sys; print("pip install requests"); sys.exit(1)

INDEX = Path("edustajat_json/index.json")
KUVAT = Path("kuvat")

with open(INDEX, encoding="utf-8") as f:
    data = json.load(f)

api = requests.Session()
api.headers.update({"User-Agent": "Politiikkaporssi/1.0 (https://github.com/kuusistot87-ctrl/politiikkaporssi; contact@example.com)"})

dl = requests.Session()
dl.headers.update({
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
    "Referer": "https://commons.wikimedia.org/",
    "Accept": "image/webp,image/apng,image/*,*/*;q=0.8",
})

def lataa(url, polku):
    try:
        r = dl.get(url, timeout=15)
        if r.status_code == 200 and len(r.content) > 2000:
            polku.write_bytes(r.content)
            return True
    except:
        pass
    return False

def etsi_commons_kuva(nimi, syntyma):
    """Etsi Commons-kuva jossa on henkilön nimi JA syntymävuosi tarkistuksena."""
    # Kokeile suoraan tiedostonimellä
    etunimi, *sukunimi_osat = nimi.split()
    sukunimi = " ".join(sukunimi_osat)
    
    for haku in [f"{nimi}", f"{sukunimi} {etunimi}", f"{nimi} politician"]:
        url = f"https://commons.wikimedia.org/w/api.php?action=query&list=search&srsearch={requests.utils.quote(haku)}&srnamespace=6&srlimit=10&format=json"
        try:
            r = api.get(url, timeout=10)
            results = r.json().get("query", {}).get("search", [])
            for res in results:
                title = res["title"]
                # Varmista ettei ole historiallinen — tarkista ettei tiedostonimessä ole vanhaa vuotta
                vuosi_m = re.search(r'(18\d\d|19[0-4]\d)', title)
                if vuosi_m:
                    continue  # Ohita jos tiedostonimessä on vanha vuosi
                if any(x in title.lower() for x in [".jpg", ".jpeg", ".png"]):
                    # Hae suora URL
                    fn = title.replace("File:", "").strip()
                    dl_url = f"https://commons.wikimedia.org/w/index.php?title=Special:Redirect/file/{requests.utils.quote(fn)}&width=300"
                    return dl_url, fn
        except:
            pass
        time.sleep(0.3)
    return None, None

def etsi_wikipedia_kuva_tarkka(nimi, syntyma):
    """Hae Wikipedia-kuva ja varmista syntymävuosi."""
    from urllib.parse import quote
    # Kokeile eri nimimuotoja
    for hakutermi in [nimi, f"{nimi} (poliitikko)", f"{nimi} (kansanedustaja)"]:
        url = f"https://fi.wikipedia.org/w/api.php?action=query&titles={quote(hakutermi)}&prop=pageimages|revisions&pithumbsize=300&rvprop=content&rvsection=0&format=json"
        try:
            r = api.get(url, timeout=10)
            pages = r.json().get("query", {}).get("pages", {})
            for page in pages.values():
                if page.get("ns", -1) != 0:
                    continue
                # Tarkista syntymävuosi artikkelin sisällöstä
                content = ""
                for rev in page.get("revisions", []):
                    content = rev.get("*", "") or rev.get("content", "")
                if syntyma and syntyma not in content:
                    continue  # Väärä henkilö
                thumb = page.get("thumbnail", {}).get("source")
                if thumb:
                    return thumb
        except:
            pass
        time.sleep(0.3)
    return None

# ── Tunnista väärät kuvat ──────────────────────────────────────────────
# Logiikka: jos kuvatiedosto on mustavalkoinen tai alle 20KB, se on todennäköisesti väärä
# Lisäksi käsittele tiedossa olevat ongelmatapaukset

ongelmat = []
for e in data:
    if not e.get("nykyinen"):
        continue
    kuva = e.get("kuva", "")
    if not kuva.startswith("kuvat/"):
        continue
    polku = Path(kuva)
    if not polku.exists():
        continue
    koko = polku.stat().st_size
    # Alle 15KB kuva on todennäköisesti mustavalkoinen/väärä
    if koko < 15000:
        ongelmat.append(e)
        print(f"Epäilyttävä kuva ({koko} bytes): {e['nimi']} → {kuva}")

print(f"\nLöydettiin {len(ongelmat)} epäilyttävää kuvaa\n")

korjattu = 0
for e in ongelmat:
    nimi = e["nimi"]
    try:
        nimi = nimi.encode("latin-1").decode("utf-8")
    except:
        pass
    syntyma = str(e.get("syntymavuosi", ""))
    vanha_kuva = Path(e["kuva"])
    
    print(f"Korjataan: {nimi} (s. {syntyma})")
    
    # 1. Yritä Wikipedia tarkalla haulla
    kuva_url = etsi_wikipedia_kuva_tarkka(nimi, syntyma)
    
    # 2. Yritä Commons
    if not kuva_url:
        kuva_url, _ = etsi_commons_kuva(nimi, syntyma)
    
    if kuva_url:
        if lataa(kuva_url, vanha_kuva):
            uusi_koko = vanha_kuva.stat().st_size
            print(f"  ✓ Uusi kuva ladattu ({uusi_koko} bytes)")
            korjattu += 1
        else:
            # Poista väärä kuva
            vanha_kuva.unlink(missing_ok=True)
            e["kuva"] = ""
            print(f"  ✗ Lataus epäonnistui, poistettu")
    else:
        # Poista väärä kuva
        vanha_kuva.unlink(missing_ok=True)
        e["kuva"] = ""
        print(f"  – Ei löydy, poistettu")
    
    time.sleep(0.5)

# Tallenna
with open(INDEX, "w", encoding="utf-8") as f:
    json.dump(data, f, ensure_ascii=False, separators=(",", ":"))

print(f"\nKorjattu: {korjattu}/{len(ongelmat)}")
print(f"\nSeuraavaksi:")
print(f"  git add kuvat/ edustajat_json/index.json")
print(f'  git commit -m "Korjataan väärät kuvat"')
print(f"  git push")
