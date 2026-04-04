#!/usr/bin/env python3
"""
Hae kaikki kansanedustajat MemberOfParliament-taulusta.
Max 100 riviä per sivu — sivutetaan oikein.

Aja: python skriptit/hae_person_ids.py
"""

import urllib.request, json, os, time

BASE = "https://avoindata.eduskunta.fi/api/v1"

def fetch(url):
    req = urllib.request.Request(url, headers={"Accept": "application/json"})
    with urllib.request.urlopen(req, timeout=15) as r:
        return json.loads(r.read().decode("utf-8"))

def hae_kaikki():
    kaikki = []
    page = 0
    while True:
        url = f"{BASE}/tables/MemberOfParliament/rows?page={page}&perPage=100"
        data = fetch(url)
        cols = data["columnNames"]
        for row in data["rowData"]:
            kaikki.append(dict(zip(cols, row)))
        print(f"  Sivu {page}: {len(data['rowData'])} riviä → yhteensä {len(kaikki)}")
        if not data["hasMore"]:
            break
        page += 1
        time.sleep(0.3)
    return kaikki

print("Haetaan MemberOfParliament (max 100/sivu)...")
edustajat = hae_kaikki()
print(f"\nYhteensä {len(edustajat)} edustajaa (kaikki aikakaudet)")

# Erottele nykyiset: puolue ei tyhjä
nykyiset = [e for e in edustajat if (e.get("party") or "").strip()]
print(f"Puolue-kenttä täynnä (=nykyiset?): {len(nykyiset)}")

# Näytä kaikki uniikit puolueet
puolueet = sorted(set((e.get("party") or "").strip() for e in edustajat if (e.get("party") or "").strip()))
print(f"\nPuolueet ({len(puolueet)} kpl):")
for p in puolueet:
    n = sum(1 for e in edustajat if (e.get("party") or "").strip() == p)
    print(f"  {n:3d}  {p}")

# Näytä 10 esimerkkiä nykyisistä
print("\nEsimerkki nykyisistä:")
for e in sorted(nykyiset, key=lambda x: x.get("lastname",""))[:10]:
    print(f"  personId={e['personId']:>5}  "
          f"{e.get('firstname',''):<15} {e.get('lastname',''):<20}  "
          f"{(e.get('party') or '')[:50]}")

# Tallenna
os.makedirs("edustajat_json", exist_ok=True)
clean = []
for e in edustajat:
    clean.append({
        "personId":  e.get("personId"),
        "etunimi":   (e.get("firstname") or "").strip(),
        "sukunimi":  (e.get("lastname") or "").strip(),
        "puolue_en": (e.get("party") or "").strip(),
        "minister":  e.get("minister"),
    })
with open("edustajat_json/api_members.json", "w", encoding="utf-8") as f:
    json.dump(clean, f, ensure_ascii=False, indent=2)
print(f"\nTallennettu: edustajat_json/api_members.json ({len(clean)} edustajaa)")

# Yhdistä omaan index.json
index_path = "edustajat_json/index.json"
if os.path.exists(index_path):
    with open(index_path, encoding="utf-8") as f:
        omat = json.load(f)
    print(f"\nYhdistetään omaan index.json:iin ({len(omat)} edustajaa)...")

    api_map = {}
    for e in edustajat:
        etu  = (e.get("firstname") or "").strip().lower()
        suku = (e.get("lastname")  or "").strip().lower()
        api_map[f"{etu} {suku}"] = e.get("personId")
        api_map[f"{suku} {etu}"] = e.get("personId")

    loydetty = 0
    ei_loydy = []
    for o in omat:
        nimi = (o.get("nimi") or "").strip()
        key  = nimi.lower()
        if key in api_map:
            o["personId"] = api_map[key]
            loydetty += 1
            continue
        osat = nimi.lower().split()
        found = False
        for i in range(1, len(osat)):
            k = " ".join(osat[i:]) + " " + " ".join(osat[:i])
            if k in api_map:
                o["personId"] = api_map[k]
                loydetty += 1
                found = True
                break
        if not found:
            ei_loydy.append(nimi)

    print(f"  Löydetty: {loydetty}/{len(omat)}")
    if ei_loydy:
        print(f"  Ei löydy ({len(ei_loydy)} kpl):")
        for n in sorted(ei_loydy):
            print(f"    - {n}")

    with open("edustajat_json/index_with_personid.json", "w", encoding="utf-8") as f:
        json.dump(omat, f, ensure_ascii=False, indent=2)
    print("  Tallennettu: edustajat_json/index_with_personid.json")

print("\nValmis!")
