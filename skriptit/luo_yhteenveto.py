#!/usr/bin/env python3
"""
luo_yhteenveto.py
=================
Luo lobbaus_json/yhteenveto.json toimintailmoituksista.
Aja: python luo_yhteenveto.py
"""
import pandas as pd, json, re
from pathlib import Path
from collections import Counter

LAHDE = Path("Toimintailmoitukset")
KOHDE = Path("lobbaus_json")

def parse_kausi(fname):
    m = re.search(r'ilmoituskausi-(\d{2})(\d{2})(\d{2})(\d{2})(\d{4})\.xlsx', fname)
    if not m: return None
    a_pv, a_kk, l_pv, l_kk, vuosi = m.groups()
    return {"id": f"{vuosi}-{a_kk}", "label": f"{a_pv}.{a_kk}–{l_pv}.{l_kk}.{vuosi}"}

def v(row, col):
    val = row.iloc[col] if col < len(row) else None
    return str(val).strip() if pd.notna(val) and str(val).strip() not in ["nan",""] else ""

def norm_tavat(tc):
    kat = {"Sähköposti":0,"Tapaaminen":0,"Puhelu":0,"Verkkovierailu":0,"Viesti/some":0,"Tapahtuma":0,"Muu":0}
    for tapa, n in tc.items():
        t = tapa.lower()
        if "hköposti" in t or "kirjeenvaihto" in t: kat["Sähköposti"] += n
        if "tapaaminen" in t or "vierailu" in t: kat["Tapaaminen"] += n
        if "puhelin" in t: kat["Puhelu"] += n
        if "verkkotapaaminen" in t: kat["Verkkovierailu"] += n
        if "tekstiviesti" in t or "pikaviesti" in t or "yksityisviesti" in t or "linkedin" in t: kat["Viesti/some"] += n
        if any(x in t for x in ["tapahtuma","tilaisuus","osallistuminen","avajaiset","julkaisu"]): kat["Tapahtuma"] += n
    total = sum(kat.values())
    raaka = sum(tc.values())
    kat["Muu"] += max(0, raaka - total)
    return {k:v for k,v in kat.items() if v > 0}

tiedostot = sorted(LAHDE.glob("avoimuusrekisteri-toimintailmoitukset*.xlsx"))
print(f"Löydetty {len(tiedostot)} tiedostoa...")

ke_c = Counter(); org_c = Counter(); aihe_c = Counter(); tapa_c = Counter()
kausi_info = {}

for f in tiedostot:
    kausi = parse_kausi(f.name)
    if not kausi: continue
    print(f"  {f.name}...")
    df = pd.read_excel(f, header=None)
    cur_org = {}; cur_aihe = ""; state = None
    kausi_ke = Counter()
    kausi_results = []
    for _, row in df.iterrows():
        c0,c1,c2,c3,c4,c5,c6,c7 = (v(row,j) for j in range(8))
        if re.match(r"^\d{6,7}-\d$", c0):
            cur_org = {"nimi": c1}; cur_aihe = ""; state = None; continue
        if c1 == "Vaikuttamistoiminnan aiheet": state = "aiheet"; continue
        if c2 == "Vaikuttamistoiminnan kohteet": state = "kohteet"; continue
        if state == "aiheet" and c1 in ["Vaikuttamistoiminta asiakkaan puolesta","Vaikuttamistoiminnan neuvonta","Vaikuttamistoiminta omaan lukuun"]:
            cur_aihe = c2[:120]; continue
        if state == "kohteet" and c5 and c5 not in ["Nimike","-","","Organisaatio"] and c6 and c6 not in ["Nimi","-",""]:
            r = {"ke": c6, "org": cur_org.get("nimi","?"), "aihe": cur_aihe, "tapa": c7}
            kausi_results.append(r)
            ke_c[c6] += 1; org_c[r["org"]] += 1
            if cur_aihe: aihe_c[cur_aihe] += 1
            if c7: tapa_c[c7] += 1
            kausi_ke[c6] += 1
    kausi_info[kausi["id"]] = {
        "label":   kausi["label"],
        "ke":      dict(kausi_ke.most_common(30)),
        "org":     dict(Counter(r["org"] for r in kausi_results).most_common(30)),
        "aiheet":  dict(Counter(r["aihe"] for r in kausi_results if r["aihe"]).most_common(20)),
        "tavat":   dict(Counter(r["tapa"] for r in kausi_results if r["tapa"]).most_common())
    }

yhteenveto = {
    "top_ke":     ke_c.most_common(30),
    "top_org":    org_c.most_common(30),
    "top_aiheet": aihe_c.most_common(20),
    "tavat":      norm_tavat(tapa_c),
    "kausi_data": kausi_info
}

out = KOHDE / "yhteenveto.json"
with open(out, "w", encoding="utf-8") as f:
    json.dump(yhteenveto, f, ensure_ascii=False, separators=(",",":"))

print(f"\nValmis! {out} ({out.stat().st_size//1024}KB)")
print(f"Top 5 KE: {ke_c.most_common(5)}")
