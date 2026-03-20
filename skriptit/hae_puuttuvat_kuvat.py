#!/usr/bin/env python3
"""
hae_puuttuvat_kuvat.py
======================
Hakee puuttuvat kuvat eduskunnan avoimesta API:sta.
Aja: python hae_puuttuvat_kuvat.py
"""
import json, re, time, urllib.request
from pathlib import Path

INDEX = Path("edustajat_json/index.json")
API   = "https://avoindata.eduskunta.fi/api/v1/tables/MemberOfParliament/rows"

def puhdista(s):
    return (s.replace("ä","a").replace("ö","o").replace("å","a")
             .replace("Ä","A").replace("Ö","O").replace("Å","A")
             .replace("é","e").replace(" ","-"))

def muodosta_kuvaurl(nimi, pid):
    osat = nimi.strip().split()
    if len(osat) < 2: return None
    etu  = puhdista(" ".join(osat[:-1]))
    suku = puhdista(osat[-1])
    return f"https://www.eduskunta.fi/FI/kansanedustajat/PublishingImages/{suku}-{etu}-web-{pid}.jpg"

def hae_personid_apiста(nimi):
    """Hakee personId:n eduskunnan APIsta nimen perusteella."""
    osat  = nimi.strip().split()
    suku  = osat[-1]
    url   = f"{API}?perPage=10&page=0&columnName=lastname&columnValue={urllib.parse.quote(suku)}"
    try:
        req = urllib.request.Request(url, headers={"User-Agent":"PolitiikkaporssiBot/1.0"})
        with urllib.request.urlopen(req, timeout=8) as r:
            data = json.loads(r.read())
        cols = data.get("columnNames",[])
        for rivi in data.get("rowData",[]):
            e = dict(zip(cols, rivi))
            fn = (e.get("firstname","") or "").strip()
            ln = (e.get("lastname","")  or "").strip()
            if ln.lower() == suku.lower() and fn and fn.split()[0].lower() == osat[0].lower():
                pid = e.get("personId","") or e.get("PersonId","")
                return str(pid) if pid else None
    except Exception as ex:
        print(f"    API-virhe ({nimi}): {ex}")
    return None

import urllib.parse

with open(INDEX, encoding="utf-8") as f:
    data = json.load(f)

puuttuvat = [e for e in data if e.get("nykyinen") and not e.get("kuva")]
print(f"Haetaan kuvia {len(puuttuvat)} edustajalle...\n")

loydetty = 0
for e in puuttuvat:
    nimi = e["nimi"]
    # Kokeile ensin eduskunta-linkistä
    pid = None
    if e.get("eduskunta"):
        m = re.search(r'/(\d+)\.aspx', e["eduskunta"])
        if m: pid = m.group(1)

    # Jos ei löydy linkistä, hae APIsta
    if not pid:
        pid = hae_personid_apiста(nimi)
        time.sleep(0.2)

    if pid:
        kuva = muodosta_kuvaurl(nimi, pid)
        e["kuva"] = kuva
        if not e.get("eduskunta"):
            e["eduskunta"] = f"https://www.eduskunta.fi/FI/kansanedustajat/Sivut/{pid}.aspx"
        loydetty += 1
        print(f"  ✓ {nimi}: {kuva}")
    else:
        print(f"  ✗ {nimi}: personId ei löydy")

with open(INDEX, "w", encoding="utf-8") as f:
    json.dump(data, f, ensure_ascii=False, separators=(",",":"))

print(f"\nValmis! Löydetty {loydetty}/{len(puuttuvat)} kuvaa.")
