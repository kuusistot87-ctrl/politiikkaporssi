#!/usr/bin/env python3
"""
hae_xml_data.py
===============
Hakee eduskunnan API:sta XML-profiilidata kaikille nykyisille edustajille
ja tallentaa ne edustajat_json/[personId]_xml.json tiedostoihin.

Aja: python hae_xml_data.py
"""
import json, time, urllib.request, re
import xml.etree.ElementTree as ET
from pathlib import Path

INDEX  = Path("edustajat_json/index.json")
KOHDE  = Path("edustajat_json")
API    = "https://avoindata.eduskunta.fi/api/v1/tables"

def hae_json(url):
    req = urllib.request.Request(url, headers={"User-Agent":"Mozilla/5.0"})
    with urllib.request.urlopen(req, timeout=10) as r:
        return json.loads(r.read())

def parsii_xml(xml_str):
    """Parsii XML-profiilin ja palauttaa sanakirjan."""
    if not xml_str: return {}
    try:
        root = ET.fromstring(xml_str)
    except: return {}

    tulos = {}

    # Sähköposti
    sp = root.findtext("SahkoPosti","")
    if sp: tulos["sahkoposti"] = sp

    # Syntymäpaikka
    sp2 = root.findtext("SyntymaPaikka","")
    if sp2: tulos["syntymapaikka"] = sp2

    # Työ- ja urahistoria
    tyot = []
    for tyo in root.findall(".//TyoUra/Tyo"):
        nimi = tyo.findtext("Nimi","")
        aika = tyo.findtext("AikaJakso","")
        if nimi: tyot.append({"nimi": nimi, "aika": aika})
    if tyot: tulos["tyoura"] = tyot

    # Valiokunnat (nykyiset + aiemmat)
    valiokunnat = []
    for osio in ["NykyisetToimielinjasenyydet","AiemmatToimielinjasenyydet"]:
        for t in root.findall(f".//{osio}/Toimielin"):
            if t.get("OnkoValiokunta") != "true": continue
            nimi = t.findtext("Nimi","")
            if not nimi: continue
            for j in t.findall("Jasenyys"):
                rooli = j.findtext("Rooli","")
                alku  = j.findtext("AlkuPvm","")
                loppu = j.findtext("LoppuPvm","")
                if rooli or alku:
                    valiokunnat.append({
                        "nimi": nimi,
                        "rooli": rooli,
                        "alku": alku,
                        "loppu": loppu
                    })
    if valiokunnat: tulos["valiokunnat"] = valiokunnat

    # Muut toimielimet (ei valiokunnat)
    muut_toimielimet = []
    for osio in ["NykyisetToimielinjasenyydet","AiemmatToimielinjasenyydet"]:
        for t in root.findall(f".//{osio}/Toimielin"):
            if t.get("OnkoValiokunta") == "true": continue
            nimi = t.findtext("Nimi","")
            if not nimi: continue
            for j in t.findall("Jasenyys"):
                rooli = j.findtext("Rooli","")
                alku  = j.findtext("AlkuPvm","")
                loppu = j.findtext("LoppuPvm","")
                if rooli or alku:
                    muut_toimielimet.append({
                        "nimi": nimi, "rooli": rooli,
                        "alku": alku, "loppu": loppu
                    })
    if muut_toimielimet: tulos["muut_toimielimet"] = muut_toimielimet

    # Ministeriydet
    ministeriydet = []
    for j in root.findall(".//ValtioneuvostonJasenyydet/Jasenyys"):
        tyyppi   = j.findtext("Ministeriys","")
        nimi     = j.findtext("Nimi","")
        hallitus = j.findtext("Hallitus","")
        alku     = j.findtext("AlkuPvm","")
        loppu    = j.findtext("LoppuPvm","")
        if nimi: ministeriydet.append({
            "tyyppi": tyyppi, "nimi": nimi,
            "hallitus": hallitus, "alku": alku, "loppu": loppu
        })
    if ministeriydet: tulos["ministeriydet"] = ministeriydet

    # Eduskuntaryhmätehtävät
    ryhma_tehtavat = []
    for osio in ["TehtavatEduskuntaryhmassa","TehtavatAiemmissaEduskuntaryhmissa"]:
        for ryhma in root.findall(f".//{osio}/Eduskuntaryhma"):
            rnimi = ryhma.findtext("Nimi","")
            for t in ryhma.findall("Tehtava"):
                rooli = t.findtext("Rooli","")
                alku  = t.findtext("AlkuPvm","")
                loppu = t.findtext("LoppuPvm","")
                if rooli: ryhma_tehtavat.append({
                    "ryhma": rnimi, "rooli": rooli,
                    "alku": alku, "loppu": loppu
                })
    if ryhma_tehtavat: tulos["ryhma_tehtavat"] = ryhma_tehtavat

    # Sidonnaisuudet (ryhmittäin)
    sidonnaisuudet = {}
    for s in root.findall(".//Sidonnaisuudet/Sidonnaisuus"):
        sidonta = s.findtext("Sidonta","")
        ryhma   = s.findtext("RyhmaOtsikko","")
        if not sidonta or not ryhma: continue
        if "ei ilmoitettavia" in sidonta.lower(): continue
        if sidonta == "----------": continue
        if ryhma not in sidonnaisuudet:
            sidonnaisuudet[ryhma] = []
        sidonnaisuudet[ryhma].append(sidonta)
    if sidonnaisuudet: tulos["sidonnaisuudet"] = sidonnaisuudet

    # Lahjailmoitukset
    lahjat = []
    for s in root.findall(".//Sidonnaisuudet/Sidonnaisuus"):
        ryhma   = s.findtext("RyhmaOtsikko","")
        sidonta = s.findtext("Sidonta","")
        if "lahjailmoitus" in ryhma.lower() and sidonta:
            lahjat.append(sidonta)
    if lahjat: tulos["lahjat"] = lahjat

    # Tuloilmoitukset
    tulot = []
    for s in root.findall(".//Sidonnaisuudet/Sidonnaisuus"):
        ryhma   = s.findtext("RyhmaOtsikko","")
        sidonta = s.findtext("Sidonta","")
        if ("tulot" in ryhma.lower() or "inkomster" in ryhma.lower()) and sidonta:
            if "ei ilmoitettavia" not in sidonta.lower():
                tulot.append({"ryhma": ryhma, "sidonta": sidonta})
    if tulot: tulos["tulot"] = tulot

    return tulos

# Lataa index.json
with open(INDEX, encoding="utf-8-sig") as f:
    data = json.load(f)

person_ids = []
for e in data:
    if not e.get("nykyinen"): continue
    m = re.search(r'/(\d+)\.aspx', e.get("eduskunta",""))
    if m: person_ids.append((m.group(1), e["nimi"]))

print(f"Haetaan {len(person_ids)} edustajan XML-profiilit...\n")

tallennettu = 0
for i, (pid, nimi) in enumerate(person_ids):
    tiedosto = KOHDE / f"{pid}_xml.json"
    if tiedosto.exists():
        tallennettu += 1
        continue  # Älä hae uudelleen

    try:
        url = f"{API}/MemberOfParliament/rows?perPage=5&page=0&columnName=personId&columnValue={pid}"
        resp  = hae_json(url)
        cols  = resp.get("columnNames",[])
        rows  = resp.get("rowData",[])
        if not rows: continue
        row   = dict(zip(cols, rows[0]))
        xml_fi = row.get("XmlDataFi","") or ""
        parsed = parsii_xml(xml_fi)
        if parsed:
            with open(tiedosto, "w", encoding="utf-8") as f:
                json.dump(parsed, f, ensure_ascii=False, separators=(",",":"))
            tallennettu += 1
        if (i+1) % 20 == 0:
            print(f"  [{i+1}/{len(person_ids)}] {nimi}")
        time.sleep(0.15)
    except Exception as ex:
        print(f"  Virhe ({nimi}): {ex}")

print(f"\nValmis! Tallennettu {tallennettu} profiilia")
print(f"Tiedostot: edustajat_json/[personId]_xml.json")
