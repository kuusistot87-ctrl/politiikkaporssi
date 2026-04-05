#!/usr/bin/env python3
"""
hae_aloitteet.py — Hakee kansanedustajien aloitteet
eduskunnan avoimesta datasta ja tallentaa JSON-tiedostoihin.

Taulu: SaliDBVpAsia (valtiopäiväasiat)
Haku:  EdustajaHenkiloNumero henkilönumerolla
Ajo:   python .github/scripts/hae_aloitteet.py
"""

import json, os, re, time, urllib.request, urllib.parse
from datetime import datetime

API_BASE   = "https://avoindata.eduskunta.fi/api/v1/tables"
ROOT       = os.getcwd()
OUT_DIR    = os.path.join(ROOT, "aloitteet_json")
INDEX_FILE = os.path.join(ROOT, "edustajat_json", "index_with_personid.json")

PER_SIVU = 100
SIVUJA   = 5      # max 500 aloitetta per edustaja
VIIVE    = 0.4

# Aloitetyypit jotka lasketaan (LA=lakialoite, KA=kirjallinen kysymys, TPA=toimenpidealoite jne.)
ALOITE_TYYPIT = {"LA", "KA", "TPA", "TA", "KAA", "VK", "MI"}

def hae_json(url):
    try:
        req = urllib.request.Request(
            url, headers={"User-Agent": "Politiikkaporssi/1.0"})
        with urllib.request.urlopen(req, timeout=15) as r:
            return json.loads(r.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        body = e.read().decode("utf-8", errors="replace")[:150]
        print(f"  VIRHE {e.code}: {body}")
        return None
    except Exception as e:
        print(f"  VIRHE: {e}")
        return None

def ascii_slug(nimi):
    korvaukset = {'ä':'a','ö':'o','å':'a','Ä':'A','Ö':'O','Å':'A'}
    s = ''.join(korvaukset.get(c, c) for c in nimi)
    return s.replace(' ', '_')

def henkilo_numero(eduskunta_url):
    m = re.search(r"/(\d+)\.aspx", eduskunta_url or "")
    return m.group(1) if m else None

def hae_aloitteet(henkilonro):
    """Hakee edustajan aloitteet EdustajaHenkiloNumero-sarakkeella."""
    kaikki, sarakkeet = [], []
    for sivu in range(SIVUJA):
        url = (f"{API_BASE}/SaliDBVpAsia/rows"
               f"?columnName=EdustajaHenkiloNumero"
               f"&columnValue={henkilonro}"
               f"&page={sivu}&perPage={PER_SIVU}")
        data = hae_json(url)
        if not data:
            break
        if not sarakkeet:
            sarakkeet = data.get("columnNames", [])
        rivit = data.get("rowData", [])
        kaikki.extend(rivit)
        if len(rivit) < PER_SIVU:
            break
        time.sleep(VIIVE)
    return sarakkeet, kaikki

def muodosta_lista(sarakkeet, rivit):
    if not sarakkeet or not rivit:
        return []

    def g(rivi, nimi):
        i = sarakkeet.index(nimi) if nimi in sarakkeet else -1
        return (rivi[i] or "").strip() if i >= 0 and i < len(rivi) else ""

    lista = []
    for rivi in rivit:
        tunnus   = g(rivi, "AsiakirjaTunnus")   # esim. "LA 5/2024 vp"
        otsikko  = g(rivi, "AsiakirjaOtsikko")
        tyyppi   = g(rivi, "AsiakirjaTyyppi")   # LA, KA, TPA jne.
        pvm      = g(rivi, "VireilletulopPvm")[:10] if g(rivi, "VireilletulopPvm") else ""
        url_p    = g(rivi, "Url")

        # Suodata vain suomenkieliset (ei RP, Motion jne.)
        if any(tunnus.startswith(r) for r in ["RP ", "Motion", "Spörsmål"]):
            continue

        lista.append({
            "tunnus":  tunnus,
            "otsikko": otsikko[:140],
            "tyyppi":  tyyppi,
            "pvm":     pvm,
            "url":     url_p
        })
    return lista

def laske_yhteenveto(lista):
    laskurit = {}
    for a in lista:
        t = a.get("tyyppi", "muu")
        laskurit[t] = laskurit.get(t, 0) + 1
    return {
        "yhteensa": len(lista),
        "tyypit":   laskurit
    }

def main():
    os.makedirs(OUT_DIR, exist_ok=True)
    if not os.path.exists(INDEX_FILE):
        print(f"VIRHE: {INDEX_FILE} ei löydy.")
        return

    with open(INDEX_FILE, "r", encoding="utf-8") as f:
        kaikki = json.load(f)

    nykyiset = [m for m in kaikki if m.get("nykyinen") and m.get("eduskunta")]
    print(f"Haetaan aloitteet {len(nykyiset)} nykyiselle edustajalle...\n")

    onnistuneet, epaonnistuneet = 0, []

    for i, ed in enumerate(nykyiset, 1):
        nimi  = ed.get("nimi", "")
        slug  = ascii_slug(nimi)
        nro   = henkilo_numero(ed.get("eduskunta", ""))
        out   = os.path.join(OUT_DIR, f"{slug}.json")

        print(f"[{i:3}/{len(nykyiset)}] {nimi} (nro:{nro})...", end=" ", flush=True)

        if not nro:
            print("ei henkilönumeroa")
            epaonnistuneet.append(nimi)
            continue

        sarakkeet, rivit = hae_aloitteet(nro)

        if not rivit:
            print("ei dataa — säilytetään vanha tiedosto")
            epaonnistuneet.append(nimi)
            continue

        lista = muodosta_lista(sarakkeet, rivit)
        yht   = laske_yhteenveto(lista)

        tulos = {
            "nimi":       nimi,
            "yhteenveto": yht,
            "aloitteet":  lista,
            "paivitetty": datetime.now().strftime("%Y-%m-%d")
        }

        with open(out, "w", encoding="utf-8") as f:
            json.dump(tulos, f, ensure_ascii=False, indent=2)

        print(f"✓ {yht['yhteensa']} aloitetta")
        onnistuneet += 1
        time.sleep(VIIVE)

    with open(os.path.join(OUT_DIR, "_meta.json"), "w", encoding="utf-8") as f:
        json.dump({
            "paivitetty":    datetime.now().strftime("%Y-%m-%d %H:%M"),
            "edustajia":     onnistuneet,
            "epaonnistuneet": epaonnistuneet
        }, f, ensure_ascii=False, indent=2)

    print(f"\n✅ Valmis! {onnistuneet}/{len(nykyiset)} edustajaa haettu.")
    if epaonnistuneet:
        print(f"⚠️  Epäonnistuneet ({len(epaonnistuneet)}): {', '.join(epaonnistuneet[:5])}")

if __name__ == "__main__":
    main()
