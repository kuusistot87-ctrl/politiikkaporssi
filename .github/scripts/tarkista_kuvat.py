#!/usr/bin/env python3
"""
tarkista_kuvat.py
=================
Tarkistaa index.json:sta kuinka monella historiallisella edustajalla
on kuva ja tulostaa raportin.

Aja: python tarkista_kuvat.py
"""

import json
from pathlib import Path
from collections import Counter

INDEX = Path("edustajat_json/index.json")

with open(INDEX, encoding="utf-8") as f:
    data = json.load(f)

historialliset = [e for e in data if not e.get("nykyinen")]
nykyiset       = [e for e in data if e.get("nykyinen")]

def on_kuva(e):
    k = e.get("kuva","")
    return bool(k and k.startswith("http"))

# Historialliset
hist_kuva     = [e for e in historialliset if on_kuva(e)]
hist_ei_kuva  = [e for e in historialliset if not on_kuva(e)]

# Nykyiset
nyk_kuva     = [e for e in nykyiset if on_kuva(e)]
nyk_ei_kuva  = [e for e in nykyiset if not on_kuva(e)]

print("=" * 55)
print("KUVIEN TARKISTUSRAPORTTI")
print("=" * 55)
print(f"\nNYKYISET ({len(nykyiset)} edustajaa):")
print(f"  Kuvallisia:   {len(nyk_kuva)}")
print(f"  Ilman kuvaa:  {len(nyk_ei_kuva)}")
if nyk_ei_kuva:
    for e in nyk_ei_kuva:
        print(f"    - {e['nimi']}")

print(f"\nHISTORIALLISET ({len(historialliset)} edustajaa):")
print(f"  Kuvallisia:   {len(hist_kuva)}")
print(f"  Ilman kuvaa:  {len(hist_ei_kuva)}")
print(f"  Kuvien lähde breakdown:")

wikimedia = sum(1 for e in hist_kuva if "wikimedia" in e.get("kuva","").lower() or "wikipedia" in e.get("kuva","").lower() or "commons" in e.get("kuva","").lower())
eduskunta = sum(1 for e in hist_kuva if "eduskunta" in e.get("kuva","").lower())
muu       = len(hist_kuva) - wikimedia - eduskunta
print(f"    Wikimedia Commons: {wikimedia}")
print(f"    Eduskunta.fi:      {eduskunta}")
print(f"    Muu:               {muu}")

print(f"\nYHTEENSÄ:")
print(f"  Kaikista {len(data)} edustajasta kuvallisia: {len(hist_kuva)+len(nyk_kuva)} ({(len(hist_kuva)+len(nyk_kuva))/len(data)*100:.0f}%)")
