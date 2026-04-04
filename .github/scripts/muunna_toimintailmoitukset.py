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
        if state == "kohteet" and c5 and c5 not in ["Nimike","-","","Organisaatio"] and c6 and c6 not in ["Nimi","-",""]:
            results.append({
                "org":    current_org.get("nimi","?"),
                "ytunnus":current_org.get("ytunnus",""),
                "aihe":   current_aihe,
                "ke":     c6,
                "nimike": c5,
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
        "tavat": Counter(),
        "nimikkeet": Counter()
    })

    for f in tiedostot:
        kausi = parse_kausi(f.name)
        if not kausi:
            print(f"  OHITETTU: {f.name}"); continue

        print(f"  Parsitaan {f.name}...")
        results = parsii_tiedosto(f)
        print(f"    → {len(results)} yhteyttä")

        # Per-KE tilastot tässä kaudessa
        ke_kausi = defaultdict(lambda: {"maara":0,"lobbarit":Counter(),"aiheet":Counter(),"tavat":Counter(),"nimikkeet":Counter()})
        for r in results:
            ke = r["ke"]
            ke_kausi[ke]["maara"] += 1
            ke_kausi[ke]["lobbarit"][r["org"]] += 1
            if r["aihe"]: ke_kausi[ke]["aiheet"][r["aihe"]] += 1
            if r["tapa"]:  ke_kausi[ke]["tavat"][r["tapa"]] += 1
            if r.get("nimike"): ke_kausi[ke]["nimikkeet"][r["nimike"]] += 1
            # Kertymä
            ke_kaikki[ke]["kaudet"][kausi["id"]] = ke_kaikki[ke]["kaudet"].get(kausi["id"],0)+1
            ke_kaikki[ke]["lobbarit"][r["org"]] += 1
            if r["aihe"]: ke_kaikki[ke]["aiheet"][r["aihe"]] += 1
            if r["tapa"]:  ke_kaikki[ke]["tavat"][r["tapa"]] += 1
            if r.get("nimike"): ke_kaikki[ke]["nimikkeet"][r["nimike"]] += 1

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
                    "tavat":        dict(d["tavat"]),
                    "nimikkeet":    dict(d["nimikkeet"])
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
            "tavat":         dict(d["tavat"].most_common()),
            "nimikkeet":     dict(d["nimikkeet"].most_common())
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

    # --- Luo yhteenveto.json lobbaus-dashboardia varten ---
    print("\nLuodaan yhteenveto.json...")

    def norm_tavat(tc):
        kat = {"Sahkoposti":0,"Tapaaminen":0,"Puhelu":0,"Verkkovierailu":0,"Viesti/some":0,"Tapahtuma":0,"Muu":0}
        for tapa, n in tc.items():
            t = tapa.lower()
            if "hköposti" in t or "kirjeenvaihto" in t: kat["Sahkoposti"] += n
            if "tapaaminen" in t or "vierailu" in t: kat["Tapaaminen"] += n
            if "puhelin" in t: kat["Puhelu"] += n
            if "verkkotapaaminen" in t: kat["Verkkovierailu"] += n
            if "tekstiviesti" in t or "pikaviesti" in t or "yksityisviesti" in t or "linkedin" in t: kat["Viesti/some"] += n
            if any(x in t for x in ["tapahtuma","tilaisuus","osallistuminen","avajaiset","julkaisu","kutsuvierastilaisuus"]): kat["Tapahtuma"] += n
        yhteensa = sum(kat.values())
        raaka = sum(tc.values())
        kat["Muu"] += max(0, raaka - yhteensa)
        # Palauta suomenkieliset nimet
        nimet = {"Sahkoposti":"Sähköposti","Tapaaminen":"Tapaaminen","Puhelu":"Puhelu",
                 "Verkkovierailu":"Verkkovierailu","Viesti/some":"Viesti/some",
                 "Tapahtuma":"Tapahtuma","Muu":"Muu"}
        return {nimet[k]:v for k,v in kat.items() if v > 0}

    ke_yht_c  = Counter()
    org_yht_c = Counter()
    aihe_yht_c = Counter()
    tapa_yht_c = Counter()
    kausi_info = {}

    for f in tiedostot:
        kausi = parse_kausi(f.name)
        if not kausi: continue
        df2 = pd.read_excel(f, header=None)
        cur_org = {}; cur_aihe = ""; state2 = None
        kausi_ke_c = Counter()
        for _, row in df2.iterrows():
            c0,c1,c2,c3,c4,c5,c6,c7 = (v(row,j) for j in range(8))
            if re.match(r"^\d{6,7}-\d$", c0):
                cur_org = {"nimi": c1}; cur_aihe = ""; state2 = None; continue
            if c1 == "Vaikuttamistoiminnan aiheet": state2 = "aiheet"; continue
            if c2 == "Vaikuttamistoiminnan kohteet": state2 = "kohteet"; continue
            if state2 == "aiheet" and c1 in ["Vaikuttamistoiminta asiakkaan puolesta","Vaikuttamistoiminnan neuvonta","Vaikuttamistoiminta omaan lukuun"]:
                cur_aihe = c2[:120]; continue
            if state2 == "kohteet" and c5 and c5 not in ["Nimike","-","","Organisaatio"] and c6 and c6 not in ["Nimi","-",""]:
                ke_yht_c[c6] += 1
                org_yht_c[cur_org.get("nimi","?")] += 1
                if cur_aihe: aihe_yht_c[cur_aihe] += 1
                if c7: tapa_yht_c[c7] += 1
                kausi_ke_c[c6] += 1
        kausi_info[kausi["id"]] = {"label": kausi["label"], "ke": dict(kausi_ke_c.most_common(30))}

    yhteenveto = {
        "top_ke":     ke_yht_c.most_common(30),
        "top_org":    org_yht_c.most_common(30),
        "top_aiheet": aihe_yht_c.most_common(20),
        "tavat":      norm_tavat(tapa_yht_c),
        "kausi_data": kausi_info
    }

    yht_out = KOHDE / "yhteenveto.json"
    with open(yht_out, "w", encoding="utf-8") as f:
        json.dump(yhteenveto, f, ensure_ascii=False, separators=(",",":"))
    print(f"  Kirjoitettu: {yht_out} ({yht_out.stat().st_size//1024}KB)")

if __name__ == "__main__":
    main()
