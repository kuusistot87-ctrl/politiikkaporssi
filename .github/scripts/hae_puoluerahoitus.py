#!/usr/bin/env python3
"""
hae_puoluerahoitus.py
Hakee eduskuntapuolueiden ajantasaiset rahoitusilmoitukset
vaalirahoitusvalvonta.fi:stä ja tallentaa JSON-tiedostoon.
"""

import requests
from bs4 import BeautifulSoup
import json
import os
import re
from datetime import datetime, timezone

# ---------------------------------------------------------------------------
# Puolueiden Y-tunnukset — haettu suoraan listaussivulta
# ---------------------------------------------------------------------------
PUOLUEET = [
    {"nimi": "Kansallinen Kokoomus",                    "lyhenne": "KOK",  "ytunnus": "0213498-5"},
    {"nimi": "Perussuomalaiset",                         "lyhenne": "PS",   "ytunnus": "0699608-4"},
    {"nimi": "Suomen Sosialidemokraattinen Puolue",      "lyhenne": "SDP",  "ytunnus": "0117005-2"},
    {"nimi": "Suomen Keskusta",                          "lyhenne": "KESK", "ytunnus": "0179288-7"},
    {"nimi": "Vihreä liitto",                            "lyhenne": "VIHR", "ytunnus": "0202918-5"},
    {"nimi": "Vasemmistoliitto",                         "lyhenne": "VAS",  "ytunnus": "0802437-3"},
    {"nimi": "Suomen ruotsalainen kansanpuolue",         "lyhenne": "RKP",  "ytunnus": "0215325-4"},
    {"nimi": "Kristillisdemokraatit",                    "lyhenne": "KD",   "ytunnus": "0117098-5"},
    {"nimi": "Liike Nyt",                                "lyhenne": "LIIK", "ytunnus": "3046798-7"},
]

BASE_URL = "https://www.vaalirahoitusvalvonta.fi"
LISTA_URL = BASE_URL + "/fi/index/puoluerahoitus/Puoluerahoitusvalvonnanilmoitukset/ajantasaisetilmoitukset.html"

def hae_sivu(url: str, timeout: int = 20) -> BeautifulSoup | None:
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

def parsii_rahasumma(teksti: str) -> float | None:
    if not teksti:
        return None
    puhdas = re.sub(r'[^\d,]', '', teksti.strip()).replace(',', '.')
    try:
        return float(puhdas) if puhdas else None
    except ValueError:
        return None

def hae_ilmoituslinkit_listalta(lista_soup: BeautifulSoup, ytunnus: str) -> list[str]:
    """Kerää linkit jotka sisältävät puolueen Y-tunnuksen."""
    linkit = []
    for a in lista_soup.find_all("a", href=True):
        href = a["href"]
        if f"/{ytunnus}/" in href and "/P_AI_" in href:
            if href.startswith("/"):
                href = BASE_URL + href
            if href not in linkit:
                linkit.append(href)
    return linkit

def parsii_ilmoitus(soup: BeautifulSoup, url: str) -> dict | None:
    tulos = {
        "url": url,
        "ilmoitusaika": None,
        "kuukausi": None,
        "vuosi": None,
        "ilmoittaja": None,
        "tuet": [],
        "summa_yhteensa": 0.0,
    }

    # Hae kuukausi+vuosi URL:sta
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

    # Ilmoittajan nimi
    taulukot = soup.find_all("table")
    for t in taulukot:
        for r in t.find_all("tr"):
            solut = r.find_all("td")
            if solut and len(solut[0].get_text(strip=True)) > 5:
                nimi = solut[0].get_text(strip=True)
                if not any(x in nimi.lower() for x in ["kuukausi", "vuosi", "yritys", "etunimi"]):
                    tulos["ilmoittaja"] = nimi[:200]
                    break
        if tulos["ilmoittaja"]:
            break

    # Tukijat ja summat
    for rivi in soup.find_all("tr"):
        solut = rivi.find_all("td")
        if len(solut) >= 3:
            nimi = solut[0].get_text(strip=True)
            if len(nimi) < 5:
                continue
            for i in range(1, len(solut)):
                summa = parsii_rahasumma(solut[i].get_text(strip=True))
                if summa and summa >= 1000:
                    ytunnus_m = re.search(r'\d{7}-\d', solut[1].get_text() if len(solut) > 1 else "")
                    tulos["tuet"].append({
                        "nimi": nimi[:200],
                        "ytunnus": ytunnus_m.group() if ytunnus_m else None,
                        "maara": summa,
                    })
                    tulos["summa_yhteensa"] += summa
                    break

    return tulos if (tulos["kuukausi"] or tulos["tuet"]) else None

def main():
    nyt = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

    output = {
        "paivitetty": nyt,
        "lahde": "vaalirahoitusvalvonta.fi",
        "puolueet": []
    }

    print(f"Haetaan päälistaussivu: {LISTA_URL}")
    lista_soup = hae_sivu(LISTA_URL)
    if not lista_soup:
        print("VIRHE: Päälistaussivu ei auennut!")
        os.makedirs("rahoitus_json", exist_ok=True)
        with open("rahoitus_json/puoluerahoitus.json", "w", encoding="utf-8") as f:
            json.dump(output, f, ensure_ascii=False, indent=2)
        return

    for puolue in PUOLUEET:
        print(f"\n=== {puolue['lyhenne']} ({puolue['ytunnus']}) ===")
        puolue_data = {**puolue, "ilmoitukset": [], "summa_per_vuosi": {}}

        linkit = hae_ilmoituslinkit_listalta(lista_soup, puolue["ytunnus"])
        print(f"  Löytyi {len(linkit)} linkkiä")

        vuosi_summat: dict[str, float] = {}
        for linkki in linkit[:36]:
            ilm_soup = hae_sivu(linkki)
            if not ilm_soup:
                continue
            ilmoitus = parsii_ilmoitus(ilm_soup, linkki)
            if ilmoitus:
                puolue_data["ilmoitukset"].append(ilmoitus)
                v = str(ilmoitus.get("vuosi", "?"))
                vuosi_summat[v] = vuosi_summat.get(v, 0) + ilmoitus["summa_yhteensa"]

        puolue_data["summa_per_vuosi"] = {k: round(v, 2) for k, v in vuosi_summat.items()}
        output["puolueet"].append(puolue_data)
        print(f"  → {len(puolue_data['ilmoitukset'])} ilmoitusta")

    os.makedirs("rahoitus_json", exist_ok=True)
    with open("rahoitus_json/puoluerahoitus.json", "w", encoding="utf-8") as f:
        json.dump(output, f, ensure_ascii=False, indent=2)
    print(f"\n✅ Tallennettu: rahoitus_json/puoluerahoitus.json")

if __name__ == "__main__":
    main()
