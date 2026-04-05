#!/usr/bin/env python3
"""
Hakee eduskunnan poissaolotilastot ja tallentaa ne JSON-muodossa.
Käyttää Playwrightia dynaamisen CSV-URL:n hakemiseen.
Ajetaan GitHub Actionsilla päivittäin.
"""

import csv, json, io, os, urllib.request
from datetime import datetime
from playwright.sync_api import sync_playwright

def hae_csv_url():
    """Hakee dynaamisen CSV-URL:n Playwrightilla."""
    csv_url = None
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(
            user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
        )
        page = context.new_page()
        def kaappaa_url(r):
            nonlocal csv_url
            if 'f4RJD' in r.url and 'dataset.csv' in r.url:
                csv_url = r.url
        page.on('request', kaappaa_url)
        page.goto('https://www.eduskunta.fi/eduskunta-ja-sen-toiminta/tilastot/kansanedustajien-poissaolot')
        page.wait_for_timeout(5000)
        browser.close()
    return csv_url

def hae_csv(url):
    """Hakee CSV:n URL:sta."""
    try:
        req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
        with urllib.request.urlopen(req, timeout=30) as r:
            return r.read().decode('utf-8')
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
                'nimi':    row['Kansanedustaja'],
                'henkilo': int(row['Henkilökohtainen syy']),
                'muu':     int(row['Muu poissaolo']),
                'yht':     int(row['Yhteensä'])
            })
        except (KeyError, ValueError) as e:
            print(f"Ohitettu rivi: {row} — {e}")

    if not rows:
        return None

    max_yht = max(r['yht'] for r in rows)
    ranked  = sorted(rows, key=lambda x: x['yht'])
    for i, r in enumerate(ranked):
        r['sijoitus'] = i + 1  # 1 = eniten poissa, 200 = vähiten poissa

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
    print("Haetaan CSV-URL Playwrightilla...")
    csv_url = hae_csv_url()
    if not csv_url:
        print("CSV-URL:n haku epäonnistui — käytetään vanhaa dataa")
        return
    print(f"CSV-URL: {csv_url}")

    csv_teksti = hae_csv(csv_url)
    if not csv_teksti:
        print("CSV:n haku epäonnistui — käytetään vanhaa dataa")
        return

    tulos = muunna_json(csv_teksti)
    if not tulos:
        print("Muunnos epäonnistui")
        return

    os.makedirs("Poissaolotilastot", exist_ok=True)
    polku = "Poissaolotilastot/poissaolot.json"
    with open(polku, 'w', encoding='utf-8') as f:
        json.dump(tulos, f, ensure_ascii=False, indent=2)

    print(f"Tallennettu {polku}")
    print(f"Edustajia: {tulos['edustajia']}, päivitetty: {tulos['paivitetty']}")

if __name__ == "__main__":
    main()
