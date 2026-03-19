#!/usr/bin/env python3
"""
luo_hakemisto.py
================
Aja tämä skripti samassa kansiossa kuin index.html:

    python luo_hakemisto.py

Lukee kaikki JSON-tiedostot edustajat_json/-kansiosta
ja luo edustajat_json/index.json -hakemistotiedoston.
"""

import json, re, sys
from pathlib import Path

KANSIO = Path("edustajat_json")

PUOLUEET = {
    "Q304191":  "KOK",
    "Q181858":  "PS",
    "Q170775":  "SDP",
    "Q499029":  "SDP",
    "Q170750":  "KESK",
    "Q1752583": "KESK",
    "Q465955":  "VIHR",
    "Q170767":  "VAS",
    "Q385927":  "VAS",
    "Q170782":  "RKP",
    "Q965052":  "KD",
    "Q3230391": "LIIK",
    "Q18678676":"SIN",
}

def kentta_id(data, avain):
    """Palauttaa @id -arvon — toimii sekä objektilla että listalla."""
    v = data.get(avain)
    if not v:
        return ""
    if isinstance(v, list):
        v = v[-1]
    if isinstance(v, dict):
        return v.get("@id", "")
    return ""

def kentta_arvo(data, avain):
    """Palauttaa @value -arvon — toimii sekä objektilla että listalla."""
    v = data.get(avain)
    if not v:
        return ""
    if isinstance(v, list):
        v = v[0]
    if isinstance(v, dict):
        return v.get("@value", "")
    return str(v)

def sama_as_lista(data):
    v = data.get("sch:sameAs", [])
    if isinstance(v, dict):
        v = [v]
    return v if isinstance(v, list) else []

def laske_vaalikaudet(data):
    rp = data.get("semparl:representative_period")
    if isinstance(rp, list):
        return len(rp)
    return 1 if rp else 0

def parsi_nimi(data):
    label = kentta_arvo(data, "skos:prefLabel")
    m = re.match(r"^(.+?),\s*(.+?)\s*\(", label)
    if m:
        return f"{m.group(2).strip()} {m.group(1).strip()}"
    return re.sub(r"\s*\(\d{4}.*\)", "", label).strip()

def parsi_vuosi(label, pattern):
    m = re.search(pattern, label)
    return m.group(1) if m else None

def parsi_edustaja(tiedosto):
    try:
        with open(tiedosto, encoding="utf-8") as f:
            data = json.load(f)
    except Exception as e:
        print(f"  VIRHE {tiedosto.name}: {e}", file=sys.stderr)
        return None

    label        = kentta_arvo(data, "skos:prefLabel")
    nimi         = parsi_nimi(data)
    party_qid    = kentta_id(data, "semparl:party").split(":")[-1].split("/")[-1]
    puolue       = PUOLUEET.get(party_qid, "–")
    kotikunta    = kentta_arvo(data, "semparl:home_location_text")
    koulutus     = kentta_arvo(data, "semparl:occupation_text")
    syntymavuosi = parsi_vuosi(label, r"\((\d{4})-")
    kuolinvuosi  = parsi_vuosi(label, r"-(\d{4})\)")
    kuva         = kentta_id(data, "sch:image")
    eid          = kentta_arvo(data, "semparl:id") or kentta_id(data, "semparl:id")
    vaalikaudet  = laske_vaalikaudet(data)
    nykyinen     = not bool(data.get("semparl:end_of_representative_period_text"))

    sa = sama_as_lista(data)
    wiki      = next((s.get("@id","") for s in sa if "fi.wikipedia.org" in s.get("@id","")), "")
    eduskunta = f"https://www.eduskunta.fi/FI/kansanedustajat/Sivut/{eid}.aspx" if eid else ""
    twitter   = next((s.get("@id","").replace("twitter:","")
                      for s in sa if s.get("@id","").startswith("twitter:")), "")

    return {
        "tiedosto":     tiedosto.name,
        "nimi":         nimi,
        "puolue":       puolue,
        "kotikunta":    kotikunta,
        "koulutus":     koulutus,
        "syntymavuosi": syntymavuosi,
        "kuolinvuosi":  kuolinvuosi,
        "kuva":         kuva,
        "wiki":         wiki,
        "eduskunta":    eduskunta,
        "twitter":      twitter,
        "vaalikaudet":  vaalikaudet,
        "nykyinen":     nykyinen,
    }

def main():
    if not KANSIO.exists():
        print(f"VIRHE: Kansiota '{KANSIO}' ei loydy.", file=sys.stderr)
        sys.exit(1)

    tiedostot = sorted(t for t in KANSIO.glob("*.json") if t.name != "index.json")
    print(f"Loydetty {len(tiedostot)} JSON-tiedostoa kansiosta '{KANSIO}'...")

    edustajat, virheet = [], 0
    for i, t in enumerate(tiedostot, 1):
        e = parsi_edustaja(t)
        if e:
            edustajat.append(e)
        else:
            virheet += 1
        if i % 200 == 0:
            print(f"  {i}/{len(tiedostot)} kasitelty...")

    edustajat.sort(key=lambda x: x["nimi"].split()[-1].lower() if x["nimi"] else "")

    kohde = KANSIO / "index.json"
    with open(kohde, "w", encoding="utf-8") as f:
        json.dump(edustajat, f, ensure_ascii=False, separators=(",", ":"))

    koko = kohde.stat().st_size
    nykyiset = sum(1 for e in edustajat if e["nykyinen"])
    print(f"\nValmis!")
    print(f"  Edustajia:      {len(edustajat)}")
    print(f"  Nykyisia:       {nykyiset}")
    print(f"  Historiallisia: {len(edustajat) - nykyiset}")
    print(f"  Virheita:       {virheet}")
    print(f"  Tiedosto:       {kohde}  ({koko/1024:.0f} KB)")

if __name__ == "__main__":
    main()
