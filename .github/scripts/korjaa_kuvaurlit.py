#!/usr/bin/env python3
"""
korjaa_kuvaurlit.py
===================
Tarkistaa nykyisten edustajien kuva-URL:it ja korjaa ne API:n kautta.
Aja: python korjaa_kuvaurlit.py
"""
import json, re, time, urllib.request, urllib.parse
from pathlib import Path

INDEX = Path("edustajat_json/index.json")
API   = "https://avoindata.eduskunta.fi/api/v1/tables/MemberOfParliament/rows"

def tarkista_url(url):
    """Palauttaa True jos URL toimii (HTTP 200)."""
    try:
        req = urllib.request.Request(url, method="HEAD",
              headers={"User-Agent":"PolitiikkaporssiBot/1.0"})
        with urllib.request.urlopen(req, timeout=5) as r:
            return r.status == 200
    except:
        return False

def hae_api(etunimi, sukunimi):
    """Hakee personId ja oikean kuva-URL:n API:sta."""
    url = f"{API}?perPage=20&page=0&columnName=lastname&columnValue={urllib.parse.quote(sukunimi)}"
    try:
        req = urllib.request.Request(url, headers={"User-Agent":"PolitiikkaporssiBot/1.0"})
        with urllib.request.urlopen(req, timeout=8) as r:
            data = json.loads(r.read())
        cols = data.get("columnNames", [])
        for rivi in data.get("rowData", []):
            e = dict(zip(cols, rivi))
            fn = (e.get("firstname","") or "").strip()
            ln = (e.get("lastname","")  or "").strip()
            # Tarkista etu- ja sukunimi
            if ln.lower() != sukunimi.lower(): continue
            if not fn: continue
            # Vertaa etunimen ensimmäistä osaa
            if fn.split()[0].lower() != etunimi.split()[0].lower(): continue
            pid = str(e.get("personId","") or e.get("PersonId","") or "").strip()
            if not pid: continue
            # Rakenna kuva-URL API:n palauttamasta datasta
            img = e.get("picture","") or e.get("Picture","") or ""
            if img and img.startswith("http"):
                return pid, img
            # Muodosta URL itse
            def p(s):
                return (s.replace("ä","a").replace("ö","o").replace("å","a")
                         .replace("Ä","A").replace("Ö","O").replace("Å","A")
                         .replace("é","e").replace(" ","-"))
            kuva = f"https://www.eduskunta.fi/FI/kansanedustajat/PublishingImages/{p(sukunimi)}-{p(etunimi)}-web-{pid}.jpg"
            return pid, kuva
    except Exception as ex:
        print(f"    API-virhe: {ex}")
    return None, None

with open(INDEX, encoding="utf-8") as f:
    data = json.load(f)

nykyiset = [e for e in data if e.get("nykyinen")]
print(f"Tarkistetaan {len(nykyiset)} nykyistä edustajaa...\n")

korjattu = 0
puuttuu  = 0

for e in nykyiset:
    nimi  = e["nimi"]
    osat  = nimi.strip().split()
    etu   = " ".join(osat[:-1])
    suku  = osat[-1]
    kuva  = e.get("kuva","")

    # Jos ei kuvaa tai URL ei toimi
    toimii = bool(kuva) and tarkista_url(kuva)
    time.sleep(0.05)

    if not toimii:
        print(f"  Haetaan: {nimi}")
        pid, uusi_kuva = hae_api(etu, suku)
        time.sleep(0.2)
        if uusi_kuva:
            e["kuva"] = uusi_kuva
            if pid and not e.get("eduskunta"):
                e["eduskunta"] = f"https://www.eduskunta.fi/FI/kansanedustajat/Sivut/{pid}.aspx"
            print(f"    ✓ {uusi_kuva}")
            korjattu += 1
        else:
            print(f"    ✗ Ei löydy")
            puuttuu += 1

with open(INDEX, "w", encoding="utf-8") as f:
    json.dump(data, f, ensure_ascii=False, separators=(",",":"))

print(f"\nValmis! Korjattu: {korjattu}, Puuttuu edelleen: {puuttuu}")
