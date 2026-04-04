#!/usr/bin/env python3
"""
hae_puoluerahoitus.py - korjattu versio
Taulukkorakenne: [Nimi | Y-tunnus | Tuen määrä | Tuki muuna kuin rahana]
"""

import requests
from bs4 import BeautifulSoup
import json
import os
import re
from datetime import datetime, timezone

PUOLUEET = [
    {"nimi": "Kansallinen Kokoomus",               "lyhenne": "KOK",  "ytunnus": "0213498-5"},
    {"nimi": "Perussuomalaiset",                    "lyhenne": "PS",   "ytunnus": "0699608-4"},
    {"nimi": "Suomen Sosialidemokraattinen Puolue", "lyhenne": "SDP",  "ytunnus": "0117005-2"},
    {"nimi": "Suomen Keskusta",                     "lyhenne": "KESK", "ytunnus": "0179288-7"},
    {"nimi": "Vihreä liitto",                       "lyhenne": "VIHR", "ytunnus": "0202918-5"},
    {"nimi": "Vasemmistoliitto",                    "lyhenne": "VAS",  "ytunnus": "0802437-3"},
    {"nimi": "Suomen ruotsalainen kansanpuolue",    "lyhenne": "RKP",  "ytunnus": "0215325-4"},
    {"nimi": "Kristillisdemokraatit",               "lyhenne": "KD",   "ytunnus": "0117098-5"},
    {"nimi": "Liike Nyt",                           "lyhenne": "LIIK", "ytunnus": "3046798-7"},
]

BASE_URL = "https://www.vaalirahoitusvalvonta.fi"
LISTA_URL = BASE_URL + "/fi/index/puoluerahoitus/Puoluerahoitusvalvonnanilmoitukset/ajantasaisetilmoitukset.html"

def hae_sivu(url, timeout=20):
    try:
        headers = {"User-Agent": "Mozilla/5.0 (compatible; PolitiikkaporssiBot/1.0)"}
        resp = requests.get(url, headers=headers, timeout=timeout)
        if resp.status_code == 200:
            return BeautifulSoup(resp.text, "lxml")
        print(f"  HTTP {resp.status_code}: {url}")
        return None
    except Exception as e:
        print(f"  Virhe: {e}")
        return None

def parsii_rahasumma(teksti):
    """Muuntaa '100 000,00' → 100000.0. Palauttaa None jos ei ole summa."""
    if not teksti:
        return None
    # Summa sisältää pilkun desimaalierottimena
    if ',' not in teksti:
        return None
    puhdas = re.sub(r'[^\d,]', '', teksti.strip()).replace(',', '.')
    try:
        arvo = float(puhdas)
        # Järkevä summa: 1 500 – 10 000 000 €
        if 1000 <= arvo <= 10_000_000:
            return arvo
        return None
    except ValueError:
        return None

def hae_ilmoituslinkit(lista_soup, ytunnus):
    linkit = []
    for a in lista_soup.find_all("a", href=True):
        href = a["href"]
        if f"/{ytunnus}/" in href and "/P_AI_" in href:
            if href.startswith("/"):
                href = BASE_URL + href
            if href not in linkit:
                linkit.append(href)
    return linkit

def parsii_ilmoitus(soup, url):
    tulos = {
        "url": url,
        "ilmoitusaika": None,
        "kuukausi": None,
        "vuosi": None,
        "ilmoittaja": None,
        "tuet": [],
        "summa_yhteensa": 0.0,
    }

    # Kuukausi + vuosi URL:sta
    m = re.search(r'/P_AI_(\d{4})(\d{2})\.html', url)
    if m:
        tulos["vuosi"] = int(m.group(1))
        tulos["kuukausi"] = int(m.group(2))

    # Saapumispäivä
    for teksti in soup.stripped_strings:
        if "saapumispäivä" in teksti.lower():
            dm = re.search(r'(\d{1,2}\.\d{1,2}\.\d{4})', teksti)
            if dm:
                tulos["ilmoitusaika"] = dm.group(1)
            break

    # Ilmoittajan nimi (ensimmäinen td jossa on isompi teksti)
    for t in soup.find_all("table"):
        for r in t.find_all("tr"):
            solut = r.find_all("td")
            if solut:
                nimi = solut[0].get_text(strip=True)
                if len(nimi) > 5 and not any(x in nimi.lower() for x in
                        ["kuukausi", "vuosi", "yritys", "etunimi", "saadun", "tuen"]):
                    tulos["ilmoittaja"] = nimi[:200]
                    break
        if tulos["ilmoittaja"]:
            break

    # Tukijat: taulukko jossa on 4+ saraketta
    # Rakenne: [Nimi | Y-tunnus | Tuen määrä | Tuki muuna kuin rahana]
    for rivi in soup.find_all("tr"):
        solut = rivi.find_all("td")
        if len(solut) < 3:
            continue
        nimi = solut[0].get_text(strip=True)
        if len(nimi) < 3:
            continue
        # Ohita otsikkorivit
        if any(x in nimi.lower() for x in ["yrityksen", "etunimet", "ilmoitus sisältää"]):
            continue
        # Y-tunnus sarakkeesta 1
        ytunnus_teksti = solut[1].get_text(strip=True) if len(solut) > 1 else ""
        ytunnus_m = re.search(r'\d{7}-\d', ytunnus_teksti)
        # Summa sarakkeesta 2 (Tuen määrä)
        summa_teksti = solut[2].get_text(strip=True) if len(solut) > 2 else ""
        summa = parsii_rahasumma(summa_teksti)
        if summa:
            tulos["tuet"].append({
                "nimi": nimi[:200],
                "ytunnus": ytunnus_m.group() if ytunnus_m else None,
                "maara": summa,
            })
            tulos["summa_yhteensa"] += summa

    return tulos if (tulos["kuukausi"] or tulos["tuet"]) else None

def main():
    nyt = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    output = {"paivitetty": nyt, "lahde": "vaalirahoitusvalvonta.fi", "puolueet": []}

    print(f"Haetaan listaussivu...")
    lista_soup = hae_sivu(LISTA_URL)
    if not lista_soup:
        print("VIRHE: Listaussivu ei auennut!")
        os.makedirs("rahoitus_json", exist_ok=True)
        with open("rahoitus_json/puoluerahoitus.json", "w", encoding="utf-8") as f:
            json.dump(output, f, ensure_ascii=False, indent=2)
        return

    for puolue in PUOLUEET:
        print(f"\n=== {puolue['lyhenne']} ({puolue['ytunnus']}) ===")
        puolue_data = {**puolue, "ilmoitukset": [], "summa_per_vuosi": {}}

        linkit = hae_ilmoituslinkit(lista_soup, puolue["ytunnus"])
        print(f"  {len(linkit)} linkkiä")

        vuosi_summat = {}
        for linkki in linkit[:36]:
            s = hae_sivu(linkki)
            if not s:
                continue
            ilm = parsii_ilmoitus(s, linkki)
            if ilm:
                puolue_data["ilmoitukset"].append(ilm)
                v = str(ilm.get("vuosi", "?"))
                vuosi_summat[v] = vuosi_summat.get(v, 0) + ilm["summa_yhteensa"]
                print(f"    {ilm['kuukausi']:02d}/{ilm['vuosi']} {ilm['ilmoittaja']}: {ilm['summa_yhteensa']:,.0f} €")

        puolue_data["summa_per_vuosi"] = {k: round(v, 2) for k, v in vuosi_summat.items()}
        output["puolueet"].append(puolue_data)

    os.makedirs("rahoitus_json", exist_ok=True)
    with open("rahoitus_json/puoluerahoitus.json", "w", encoding="utf-8") as f:
        json.dump(output, f, ensure_ascii=False, indent=2)
    print(f"\n✅ Valmis: rahoitus_json/puoluerahoitus.json")

if __name__ == "__main__":
    main()
