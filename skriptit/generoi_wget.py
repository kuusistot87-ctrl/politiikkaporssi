#!/usr/bin/env python3
"""
generoi_wget.py
Luo wget_kuvat.bat - aja se komentoriviltä ladataksesi kuvat
"""
import json, re
from pathlib import Path

INDEX = Path("edustajat_json/index.json")

with open(INDEX, encoding="utf-8-sig") as f:
    data = json.load(f)

nykyiset = [e for e in data if e.get("nykyinen") and e.get("kuva","").startswith("http")]

# Kirjoita .bat-tiedosto
bat = ['@echo off', 'mkdir kuvat 2>nul', 'echo Ladataan %d kuvaa...' % len(nykyiset), '']

for e in nykyiset:
    url = e["kuva"]
    m = re.search(r'-web-(\d+)\.jpg', url)
    if not m: continue
    pid = m.group(1)
    bat.append(f'if not exist "kuvat\\{pid}.jpg" curl -s -L -A "Mozilla/5.0 (Windows NT 10.0; Win64; x64)" -H "Referer: https://www.eduskunta.fi/" -o "kuvat\\{pid}.jpg" "{url}"')

bat += ['', 'echo Valmis!', 'pause']

with open("wget_kuvat.bat","w",encoding="utf-8") as f:
    f.write('\n'.join(bat))

print(f"Kirjoitettu wget_kuvat.bat ({len(nykyiset)} kuvaa)")
print("Aja: wget_kuvat.bat")
