#!/usr/bin/env python3
"""
hae_puoluerahoitus.py
Hakee eduskuntapuolueiden ajantasaiset rahoitusilmoitukset
vaalirahoitusvalvonta.fi:stä ja tallentaa JSON-tiedostoon.

Ajantasaiset ilmoitukset = kuukausittaiset tukitiedot (≥1500€ / ≥2000€ 1.7.2025 alkaen)
"""

import requests
from bs4 import BeautifulSoup
import json
import os
import re
from datetime import datetime, timezone

# ---------------------------------------------------------------------------
# Puolueiden Y-tunnukset ja nimet
# Löydetty vaalirahoitusvalvonta.fi URL-rakenteesta
# ---------------------------------------------------------------------------
PUOLUEET = [
    {"nimi": "Kansallinen Kokoomus",   "lyhenne": "KOK", "ytunnus": "0201810-9"},
    {"nimi": "Perussuomalaiset",        "lyhenne": "PS",  "ytunnus": "0699608-4"},
    {"nimi": "Suomen Sosialidemokraattinen Puolue", "lyhenne": "SDP", "ytunnus": "0117005-2"},
    {"nimi": "Suomen Keskusta",         "lyhenne": "KESK","ytunnus": "0179288-7"},
    {"nimi": "Vihreä liitto",           "lyhenne": "VIHR","ytunnus": "0202918-5"},
    {"nimi": "Vasemmistoliitto",        "lyhenne": "VAS", "ytunnus": "0202115-1"},
    {"nimi": "Suomen ruotsalainen kansanpuolue", "lyhenne": "RKP", "ytunnus": "0116822-0"},
    {"nimi": "Kristillisdemokraatit",   "lyhenne": "KD",  "ytunnus": "0117098-5"},
    {"nimi": "Liike Nyt",               "lyhenne": "LIIK","ytunnus": "3046798-7"},
]

BASE_URL = "https://www.vaalirahoitusvalvonta.fi"

# Ilmoituslistauksen URL per puolue
def lista_url(ytunnus: str, vuosi: int) -> str:
    return (
        f"{BASE_URL}/fi/index/puoluerahoitus/Puoluerahoitusvalvonnanilmoitukset"
        f"/ajantasaisetilmoitukset/{vuosi}/{ytunnus}.html"
    )

def hae_sivu(url: str, timeout: int = 15) -> BeautifulSoup | None:
    """Hakee URL:n ja palauttaa BeautifulSoup-objektin tai None virheen sattuessa."""
    try:
        headers = {"User-Agent": "Mozilla/5.0 (compatible; PolitiikkaporssiBot/1.0)"}
        resp = requests.get(url, headers=headers, timeout=timeout)
        if resp.status_code == 200:
            return BeautifulSoup(resp.text, "lxml")
        else:
            print(f"  HTTP {resp.status_code}: {url}")
            return None
    except Exception as e:
        print(f"  Virhe haussa {url}: {e}")
        return None

def parsii_rahasumma(teksti: str) -> float | None:
    """Muuntaa '30 000,00' → 30000.0"""
    if not teksti:
        return None
    puhdas = re.sub(r'[^\d,]', '', teksti.strip()).replace(',', '.')
    try:
        return float(puhdas)
    except ValueError:
        return None

def hae_ilmoituslinkki(lista_soup: BeautifulSoup) -> list[str]:
    """Kerää yksittäisten ilmoitusten linkit listaussivulta."""
    linkit = []
    for a in lista_soup.find_all("a", href=True):
        href = a["href"]
        if "/P_AI_" in href:
            if href.startswith("/"):
                href = BASE_URL + href
            if href not in linkit:
                linkit.append(href)
    return linkit

def parsii_ilmoitus(soup: BeautifulSoup, url: str) -> dict | None:
    """Parsii yksittäisen ajantasaisen ilmoituksen sisällön."""
    tulos = {
        "url": url,
        "ilmoitusaika": None,
        "kuukausi": None,
        "vuosi": None,
        "tuet": [],
        "summa_yhteensa": 0.0,
    }

    # Yritä löytää "Tuki ajalta" -taulukko
    taulukot = soup.find_all("table")
    for taulukko in taulukot:
        teksti = taulukko.get_text(separator=" ")
        # Etsi kuukausi + vuosi
        m = re.search(r'(\d{1,2})\s+(\d{4})', teksti)
        if m and not tulos["kuukausi"]:
            tulos["kuukausi"] = int(m.group(1))
            tulos["vuosi"] = int(m.group(2))

    # Kerää tukijat
    for rivi in soup.find_all("tr"):
        solut = rivi.find_all("td")
        if len(solut) >= 3:
            nimi_solu = solut[0].get_text(strip=True)
            # Tarkista onko summa-sarake järkevä (sisältää pilkun tai välilyöntiä)
            for i in range(1, len(solut)):
                summa_teksti = solut[i].get_text(strip=True)
                summa = parsii_rahasumma(summa_teksti)
                if summa and summa >= 1000:
                    ytunnus_m = re.search(r'\d{7}-\d', solut[1].get_text() if len(solut) > 1 else "")
                    tulos["tuet"].append({
                        "nimi": nimi_solu[:200],
                        "ytunnus": ytunnus_m.group() if ytunnus_m else None,
                        "maara": summa,
                    })
                    tulos["summa_yhteensa"] += summa
                    break

    # Saapumispäivä tekstistä
    saapuminen = soup.find(string=re.compile(r'saapumispäivä'))
    if saapuminen:
        p = saapuminen.parent.get_text(separator=" ") if saapuminen.parent else ""
        dm = re.search(r'(\d{1,2}\.\d{1,2}\.\d{4})', p)
        if dm:
            tulos["ilmoitusaika"] = dm.group(1)

    return tulos if (tulos["kuukausi"] or tulos["tuet"]) else None

def main():
    nyt = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    vuosi_nyt = datetime.now(timezone.utc).year

    output = {
        "paivitetty": nyt,
        "lahde": "vaalirahoitusvalvonta.fi",
        "puolueet": []
    }

    for puolue in PUOLUEET:
        print(f"\n=== {puolue['lyhenne']} ({puolue['ytunnus']}) ===")
        puolue_data = {
            **puolue,
            "ilmoitukset": [],
            "summa_per_vuosi": {}
        }

        # Hae 2–3 vuotta taaksepäin
        for vuosi in range(vuosi_nyt - 1, vuosi_nyt + 1):
            url = lista_url(puolue["ytunnus"], vuosi)
            print(f"  Haetaan lista: {url}")
            lista_soup = hae_sivu(url)
            if not lista_soup:
                continue

            linkit = hae_ilmoituslinkki(lista_soup)
            print(f"  Löytyi {len(linkit)} ilmoitusta vuodelle {vuosi}")

            vuosi_summa = 0.0
            for linkki in linkit[:24]:  # max 24 per vuosi (2/kk)
                ilm_soup = hae_sivu(linkki)
                if not ilm_soup:
                    continue
                ilmoitus = parsii_ilmoitus(ilm_soup, linkki)
                if ilmoitus:
                    ilmoitus["haettu_vuosi"] = vuosi
                    puolue_data["ilmoitukset"].append(ilmoitus)
                    vuosi_summa += ilmoitus["summa_yhteensa"]

            if vuosi_summa > 0:
                puolue_data["summa_per_vuosi"][str(vuosi)] = round(vuosi_summa, 2)

        output["puolueet"].append(puolue_data)
        print(f"  → Yhteensä {len(puolue_data['ilmoitukset'])} ilmoitusta")

    # Tallenna
    os.makedirs("rahoitus_json", exist_ok=True)
    polku = "rahoitus_json/puoluerahoitus.json"
    with open(polku, "w", encoding="utf-8") as f:
        json.dump(output, f, ensure_ascii=False, indent=2)
    print(f"\n✅ Tallennettu: {polku}")
    print(f"   Puolueita: {len(output['puolueet'])}")
    total = sum(
        sum(v for v in p["summa_per_vuosi"].values())
        for p in output["puolueet"]
    )
    print(f"   Tuet yhteensä: {total/1e6:.2f} M€")

if __name__ == "__main__":
    main()
