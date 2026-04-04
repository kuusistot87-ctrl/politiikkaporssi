#!/usr/bin/env python3
"""
Hakee eduskunnan poissaolotilastot ja tallentaa ne JSON-muodossa.
Ajetaan GitHub Actionsilla päivittäin.
"""

import csv
import json
import io
import os
import requests
from datetime import datetime

# Datawrapper CSV-URL (päivitetään jos muuttuu)
CSV_URL = "https://datawrapper.dwcdn.net/f4RJD/full.csv"

def hae_csv():
    """Hakee CSV:n Datawrapperista."""
    try:
        r = requests.get(CSV_URL, timeout=30)
        r.raise_for_status()
        return r.text
    except Exception as e:
        print(f"Virhe CSV:n haussa: {e}")
        return None

def muunna_json(csv_teksti):
    """Muuntaa CSV:n JSON-muotoon."""
    reader = csv.DictReader(io.StringIO(csv_teksti))
    rows = []
    for row in reader:
        try:
            rows.append({
                'nimi':     row['Kansanedustaja'],
                'henkilo':  int(row['Henkilökohtainen syy']),
                'muu':      int(row['Muu poissaolo']),
                'yht':      int(row['Yhteensä'])
            })
        except (KeyError, ValueError) as e:
            print(f"Ohitettu rivi: {row} — {e}")

    if not rows:
        return None

    max_yht = max(r['yht'] for r in rows)
    ranked  = sorted(rows, key=lambda x: x['yht'], reverse=True)
    for i, r in enumerate(ranked):
        r['sijoitus'] = i + 1

    data = {r['nimi']: {
        'henkilo':  r['henkilo'],
        'muu':      r['muu'],
        'yht':      r['yht'],
        'sijoitus': r['sijoitus']
    } for r in ranked}

    return {
        'paivitetty': datetime.now().strftime('%d.%m.%Y'),
        'max_yht':    max_yht,
        'edustajia':  len(data),
        'data':       data
    }

def main():
    print("Haetaan poissaolotilastot...")
    csv_teksti = hae_csv()

    if not csv_teksti:
        print("CSV:n haku epäonnistui — käytetään vanhaa dataa")
        return

    tulos = muunna_json(csv_teksti)
    if not tulos:
        print("Muunnos epäonnistui")
        return

    # Varmistetaan hakemisto
    os.makedirs("Poissaolotilastot", exist_ok=True)
    polku = "Poissaolotilastot/poissaolot.json"

    with open(polku, 'w', encoding='utf-8') as f:
        json.dump(tulos, f, ensure_ascii=False, indent=2)

    print(f"Tallennettu {polku}")
    print(f"Edustajia: {tulos['edustajia']}, päivitetty: {tulos['paivitetty']}")

if __name__ == "__main__":
    main()
