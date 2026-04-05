#!/usr/bin/env python3
"""
hae_aktiivisuus.py — Hakee kansanedustajien aktiivisuusluvut
eduskunnan tyo-eduskunnassa-sivulta Playwrightilla.

Hakee: Aloitteet, Kirjalliset kysymykset, Suulliset kysymykset,
       Puheenvuorot, Äänestäminen

Ajo: python .github/scripts/hae_aktiivisuus.py
"""

import json, os, re, time
from datetime import datetime
from playwright.sync_api import sync_playwright

ROOT       = os.getcwd()
OUT_DIR    = os.path.join(ROOT, "aktiivisuus_json")
INDEX_FILE = os.path.join(ROOT, "edustajat_json", "index_with_personid.json")
VIIVE      = 1.0

def ascii_slug(nimi):
    korvaukset = {'ä':'a','ö':'o','å':'a','Ä':'A','Ö':'O','Å':'A'}
    s = ''.join(korvaukset.get(c, c) for c in nimi)
    return s.replace(' ', '_')

def henkilo_numero(eduskunta_url):
    m = re.search(r"/(\d+)\.aspx", eduskunta_url or "")
    if m:
        return m.group(1)
    m = re.search(r"/kansanedustajat/(\d+)", eduskunta_url or "")
    return m.group(1) if m else None

def hae_luvut(page, person_id):
    url = f"https://www.eduskunta.fi/kansanedustajat-ja-toimielimet/kansanedustajat/{person_id}/tyo-eduskunnassa"
    try:
        page.goto(url, timeout=30000, wait_until="domcontentloaded")
        page.wait_for_timeout(2000)

        tulos = {
            "aloitteet": 0,
            "kirjalliset_kysymykset": 0,
            "suulliset_kysymykset": 0,
            "puheenvuorot": 0,
            "aanestaminen": 0
        }

        # Hae kaikki accordion-otsikot joissa on luku suluissa
        items = page.query_selector_all("button, h2, h3, .accordion, [class*='accordion'], [class*='item']")
        
        for el in items:
            teksti = el.inner_text().strip()
            # Etsi muoto "Aloitteet (2)"
            m = re.search(r'(Aloitteet|Kirjalliset kysymykset|Suulliset kysymykset|Puheenvuorot|Äänestäminen)\s*\((\d+)\)', teksti)
            if m:
                kategoria = m.group(1)
                luku = int(m.group(2))
                if kategoria == "Aloitteet":
                    tulos["aloitteet"] = luku
                elif kategoria == "Kirjalliset kysymykset":
                    tulos["kirjalliset_kysymykset"] = luku
                elif kategoria == "Suulliset kysymykset":
                    tulos["suulliset_kysymykset"] = luku
                elif kategoria == "Puheenvuorot":
                    tulos["puheenvuorot"] = luku
                elif kategoria == "Äänestäminen":
                    tulos["aanestaminen"] = luku

        return tulos
    except Exception as e:
        print(f"  VIRHE: {e}")
        return None

def main():
    os.makedirs(OUT_DIR, exist_ok=True)
    if not os.path.exists(INDEX_FILE):
        print(f"VIRHE: {INDEX_FILE} ei löydy.")
        return

    with open(INDEX_FILE, "r", encoding="utf-8") as f:
        kaikki = json.load(f)

    nykyiset = [m for m in kaikki if m.get("nykyinen") and m.get("eduskunta")]
    print(f"Haetaan aktiivisuusdata {len(nykyiset)} nykyiselle edustajalle...\n")

    onnistuneet, epaonnistuneet = 0, []

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        page.set_extra_http_headers({"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"})

        for i, ed in enumerate(nykyiset, 1):
            nimi   = ed.get("nimi", "")
            slug   = ascii_slug(nimi)
            nro    = henkilo_numero(ed.get("eduskunta", ""))
            out    = os.path.join(OUT_DIR, f"{slug}.json")

            print(f"[{i:3}/{len(nykyiset)}] {nimi} (nro:{nro})...", end=" ", flush=True)

            if not nro:
                print("ei henkilönumeroa")
                epaonnistuneet.append(nimi)
                continue

            luvut = hae_luvut(page, nro)

            if not luvut:
                print("ei dataa — säilytetään vanha tiedosto")
                epaonnistuneet.append(nimi)
                continue

            tulos = {
                "nimi":       nimi,
                "luvut":      luvut,
                "paivitetty": datetime.now().strftime("%Y-%m-%d")
            }

            with open(out, "w", encoding="utf-8") as f:
                json.dump(tulos, f, ensure_ascii=False, indent=2)

            print(f"✓ aloitteet:{luvut['aloitteet']} kk:{luvut['kirjalliset_kysymykset']} pv:{luvut['puheenvuorot']}")
            onnistuneet += 1
            time.sleep(VIIVE)

        browser.close()

    with open(os.path.join(OUT_DIR, "_meta.json"), "w", encoding="utf-8") as f:
        json.dump({
            "paivitetty":     datetime.now().strftime("%Y-%m-%d %H:%M"),
            "edustajia":      onnistuneet,
            "epaonnistuneet": epaonnistuneet
        }, f, ensure_ascii=False, indent=2)

    print(f"\n✅ Valmis! {onnistuneet}/{len(nykyiset)} edustajaa haettu.")

if __name__ == "__main__":
    main()
