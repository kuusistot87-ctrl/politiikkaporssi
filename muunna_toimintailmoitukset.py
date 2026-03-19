#!/usr/bin/env python3
"""
muunna_toimintailmoitukset.py
=============================
Muuntaa avoimuusrekisterin toimintailmoitus-Excel-tiedostot JSON-muotoon.

Aja: python muunna_toimintailmoitukset.py

Lukee kaikki avoimuusrekisteri-toimintailmoitukset*.xlsx tiedostot kansiosta
"Toimintailmoitukset" ja kirjoittaa JSON:t kansioon "lobbaus_json/".
"""

import pandas as pd, json, re, sys
from pathlib import Path
from collections import defaultdict, Counter

LAHDE = Path("Toimintailmoitukset")
KOHDE = Path("lobbaus_json")

def parse_kausi(fname):
    m = re.search(r'ilmoituskausi-(\d{2})(\d{2})(\d{2})(\d{2})(\d{4})\.xlsx', fname)
    if not m: return None
    a_pv, a_kk, l_pv, l_kk, vuosi = m.groups()
    return {
        "id":       f"{vuosi}-{a_kk}",
        "label":    f"{a_pv}.{a_kk}–{l_pv}.{l_kk}.{vuosi}",
        "tiedosto": f"ti-{vuosi}-{a_kk}.json"
    }

def v(row, col):
    val = row.iloc[col] if col < len(row) else None
    return str(val).strip() if pd.notna(val) and str(val).strip() not in ["nan",""] else ""

def parsii_tiedosto(f):
    df = pd.read_excel(f, header=None)
    results = []
    current_org = {}
    current_aihe = ""
    state = None

    for _, row in df.iterrows():
        c0,c1,c2,c3,c4,c5,c6,c7 = (v(row,j) for j in range(8))

        if re.match(r'^\d{6,7}-\d$', c0):
            current_org = {"ytunnus": c0, "nimi": c1, "kausi": c2}
            current_aihe = ""
            state = None
            continue
        if c1 == "Vaikuttamistoiminnan aiheet":
            state = "aiheet"; continue
        if c2 == "Vaikuttamistoiminnan kohteet":
            state = "kohteet"; continue
        if state == "aiheet" and c1 in [
            "Vaikuttamistoiminta asiakkaan puolesta",
            "Vaikuttamistoiminnan neuvonta",
            "Vaikuttamistoiminta omaan lukuun"
        ]:
            current_aihe = c2[:120] if c2 else ""
            continue
        if state == "kohteet" and c5 == "Kansanedustaja" and c6 and c6 != "Nimi":
            results.append({
                "org":    current_org.get("nimi","?"),
                "ytunnus":current_org.get("ytunnus",""),
                "aihe":   current_aihe,
                "ke":     c6,
                "tapa":   c7
            })
    return results

def main():
    if not LAHDE.exists():
        print(f"VIRHE: Kansiota '{LAHDE}' ei löydy.", file=sys.stderr)
        sys.exit(1)

    KOHDE.mkdir(exist_ok=True)
    tiedostot = sorted(LAHDE.glob("avoimuusrekisteri-toimintailmoitukset*.xlsx"))
    if not tiedostot:
        print("VIRHE: Tiedostoja ei löydy.", file=sys.stderr)
        sys.exit(1)

    print(f"Löydetty {len(tiedostot)} tiedostoa...")

    # Per-KE aggregaatti kaikista kausista: nimi → {kaudet, lobbarit, aiheet, tavat}
    ke_kaikki = defaultdict(lambda: {
        "kaudet": {},       # kausi_id → maara
        "lobbarit": Counter(),
        "aiheet": Counter(),
        "tavat": Counter()
    })

    for f in tiedostot:
        kausi = parse_kausi(f.name)
        if not kausi:
            print(f"  OHITETTU: {f.name}"); continue

        print(f"  Parsitaan {f.name}...")
        results = parsii_tiedosto(f)
        print(f"    → {len(results)} yhteyttä")

        # Per-KE tilastot tässä kaudessa
        ke_kausi = defaultdict(lambda: {"maara":0,"lobbarit":Counter(),"aiheet":Counter(),"tavat":Counter()})
        for r in results:
            ke = r["ke"]
            ke_kausi[ke]["maara"] += 1
            ke_kausi[ke]["lobbarit"][r["org"]] += 1
            if r["aihe"]: ke_kausi[ke]["aiheet"][r["aihe"]] += 1
            if r["tapa"]:  ke_kausi[ke]["tavat"][r["tapa"]] += 1
            # Kertymä
            ke_kaikki[ke]["kaudet"][kausi["id"]] = ke_kaikki[ke]["kaudet"].get(kausi["id"],0)+1
            ke_kaikki[ke]["lobbarit"][r["org"]] += 1
            if r["aihe"]: ke_kaikki[ke]["aiheet"][r["aihe"]] += 1
            if r["tapa"]:  ke_kaikki[ke]["tavat"][r["tapa"]] += 1

        # Organisaatiotilastot
        org_stats = Counter(r["org"] for r in results)

        # Kirjoita kausikohtainen tiedosto
        kausi_json = {
            "kausi": kausi,
            "yhteydet_yhteensa": len(results),
            "kansanedustajat": {
                ke: {
                    "maara": d["maara"],
                    "top_lobbarit": d["lobbarit"].most_common(5),
                    "top_aiheet":   d["aiheet"].most_common(3),
                    "tavat":        dict(d["tavat"])
                }
                for ke, d in ke_kausi.items()
            },
            "top_lobbarit": org_stats.most_common(30)
        }

        out = KOHDE / kausi["tiedosto"]
        with open(out, "w", encoding="utf-8") as fh:
            json.dump(kausi_json, fh, ensure_ascii=False, separators=(",",":"))
        print(f"    Kirjoitettu: {out.name} ({out.stat().st_size//1024}KB)")

    # Pääindeksin KE-tiedot (lisätään lobbaus_json/index.json:iin)
    idx_path = KOHDE / "index.json"
    if idx_path.exists():
        with open(idx_path, encoding="utf-8") as f:
            idx = json.load(f)
    else:
        idx = {"kaudet":[], "kansanedustajat":{}}

    # Lisää toimintailmoitusdata KE:ille
    idx["toimintailmoitukset"] = {
        ke: {
            "yhteensa":      sum(d["kaudet"].values()),
            "kaudet":        d["kaudet"],
            "top_lobbarit":  d["lobbarit"].most_common(10),
            "top_aiheet":    d["aiheet"].most_common(5),
            "tavat":         dict(d["tavat"].most_common())
        }
        for ke, d in ke_kaikki.items()
    }

    with open(idx_path, "w", encoding="utf-8") as f:
        json.dump(idx, f, ensure_ascii=False, separators=(",",":"))

    print(f"\nValmis!")
    print(f"  KE:tä indeksissä: {len(ke_kaikki)}")
    top5 = sorted(ke_kaikki.items(), key=lambda x: -sum(x[1]['kaudet'].values()))[:5]
    print("  Top 5:")
    for ke, d in top5:
        print(f"    {ke}: {sum(d['kaudet'].values())} yht, top lobbari: {d['lobbarit'].most_common(1)}")

if __name__ == "__main__":
    main()
