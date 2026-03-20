#!/usr/bin/env python3
"""
korjaa_puuttuvat_kuvat.py
=========================
Lisää kuvat käsin niille nykyisille edustajille joilta puuttuu kuva.
Aja: python korjaa_puuttuvat_kuvat.py
"""
import json
from pathlib import Path

INDEX = Path("edustajat_json/index.json")

KUVAT = {
    "Anette Karlsson": "https://www.eduskunta.fi/FI/kansanedustajat/PublishingImages/Karlsson-Anette-web-911831.jpg",
    "Henrik Vuornos":  "https://www.eduskunta.fi/FI/kansanedustajat/PublishingImages/Vuornos-Henrik-web-911828.jpg",
    "Mauri Kontu":     "https://www.eduskunta.fi/FI/kansanedustajat/PublishingImages/Kontu-Mauri-web-911830.jpg",
}

EDUSKUNTA = {
    "Anette Karlsson": "https://www.eduskunta.fi/FI/kansanedustajat/Sivut/911831.aspx",
    "Henrik Vuornos":  "https://www.eduskunta.fi/FI/kansanedustajat/Sivut/911828.aspx",
    "Mauri Kontu":     "https://www.eduskunta.fi/FI/kansanedustajat/Sivut/911830.aspx",
}

with open(INDEX, encoding="utf-8") as f:
    data = json.load(f)

paivitetty = 0
for e in data:
    if e["nimi"] in KUVAT:
        e["kuva"]      = KUVAT[e["nimi"]]
        e["eduskunta"] = EDUSKUNTA[e["nimi"]]
        paivitetty += 1
        print(f"  ✓ {e['nimi']}: {e['kuva']}")

with open(INDEX, "w", encoding="utf-8") as f:
    json.dump(data, f, ensure_ascii=False, separators=(",",":"))

print(f"\nPäivitetty {paivitetty} edustajaa.")
