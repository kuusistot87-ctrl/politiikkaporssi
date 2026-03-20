#!/usr/bin/env python3
"""
paivita_vaalikaudet.py
Parsii vaalikaudet XmlDataFi-kentästä ja päivittää index.json:iin.
Aja: python paivita_vaalikaudet.py
"""
import json, time, urllib.request, re, xml.etree.ElementTree as ET
from pathlib import Path

INDEX = Path("edustajat_json/index.json")
API   = "https://avoindata.eduskunta.fi/api/v1/tables"

# Suomen eduskuntavaalivuodet → vaalikauden alku ja loppu
VAALIVUODET = [
    ("1999","2003"), ("2003","2007"), ("2007","2011"),
    ("2011","2015"), ("2015","2019"), ("2019","2023"), ("2023","2027"),
]

def vaalikaudet_alkupvm(alku_str):
    """Palauttaa listan (alku, loppu) -tupleja alkupäivämäärän perusteella."""
    # alku_str esim. "21.03.2007"
    m = re.search(r'(\d{4})$', alku_str)
    if not m: return []
    alku_vuosi = m.group(1)
    return [(a, l) for a, l in VAALIVUODET if a >= alku_vuosi]

def hae_json(url):
    req = urllib.request.Request(url, headers={"User-Agent":"Mozilla/5.0"})
    with urllib.request.urlopen(req, timeout=10) as r:
        return json.loads(r.read())

with open(INDEX, encoding="utf-8-sig") as f:
    data = json.load(f)

person_ids = []
for e in data:
    if not e.get("nykyinen"): continue
    m = re.search(r'/(\d+)\.aspx', e.get("eduskunta",""))
    if m: person_ids.append((m.group(1), e["nimi"]))

print(f"Haetaan {len(person_ids)} edustajan tiedot API:sta...")

pid_info = {}
for i, (pid, nimi) in enumerate(person_ids):
    try:
        url = f"{API}/MemberOfParliament/rows?perPage=5&page=0&columnName=personId&columnValue={pid}"
        resp = hae_json(url)
        cols = resp.get("columnNames", [])
        rows = resp.get("rowData", [])
        if not rows: continue
        row = dict(zip(cols, rows[0]))

        # Parsii XML
        xml_str = row.get("XmlDataFi","") or ""
        if not xml_str: continue

        root = ET.fromstring(xml_str)
        ns = ""

        # Hae edustajatoimen alkupäivä
        alku = ""
        for et in root.findall(".//Edustajatoimi"):
            a = et.findtext("AlkuPvm","")
            if a and (not alku or a < alku):
                alku = a

        # Laske vaalikaudet
        kaudet = vaalikaudet_alkupvm(alku) if alku else []

        pid_info[pid] = {
            "kaudet": kaudet,
            "alku":   alku
        }

        if (i+1) % 20 == 0:
            print(f"  [{i+1}/{len(person_ids)}] {nimi}: {alku} → {len(kaudet)} kautta")
        time.sleep(0.15)
    except Exception as ex:
        print(f"  Virhe ({nimi}): {ex}")

print(f"\nData haettu {len(pid_info)} edustajalle")

# Päivitä index.json
paivitetty = 0
for e in data:
    if not e.get("nykyinen"): continue
    m = re.search(r'/(\d+)\.aspx', e.get("eduskunta",""))
    if not m: continue
    pid  = m.group(1)
    info = pid_info.get(pid)
    if not info or not info["kaudet"]: continue

    kaudet = info["kaudet"]
    kausi_str = ", ".join(
        f"{a}–{b}" if b != "2027" else f"{a}–"
        for a, b in kaudet
    )
    e["vaalikaudet_lista"] = kausi_str
    e["vaalikaudet"]       = len(kaudet)
    paivitetty += 1

with open(INDEX, "w", encoding="utf-8") as f:
    json.dump(data, f, ensure_ascii=False, separators=(",",":"))

print(f"Päivitetty {paivitetty} edustajaa\n")

# Esimerkkejä
for nimi in ["Petteri Orpo", "Li Andersson", "Anna-Kaisa Ikonen"]:
    e = next((e for e in data if e.get("nimi") == nimi), None)
    if e: print(f"  {nimi}: {e.get('vaalikaudet_lista','?')}")
