"""
hae_ohjelmat.py — Hakee eduskuntapuolueiden ohjelmat Pohtivasta
ja tallentaa ne JSON-tiedostoiksi ohjelmat_json/-kansioon.

Käyttö:
    pip install requests beautifulsoup4
    python hae_ohjelmat.py

Luo tiedostot:
    ohjelmat_json/kok_vaali2023.json
    ohjelmat_json/kok_periaate2018.json
    jne.
"""

import json
import time
import pathlib
import requests
from bs4 import BeautifulSoup

OUTPUT_DIR = pathlib.Path("ohjelmat_json")
OUTPUT_DIR.mkdir(exist_ok=True)

BASE = "https://www.fsd.tuni.fi"

OHJELMAT = [
    { "id": "kok_vaali2023",      "url": f"{BASE}/pohtiva/ohjelmalistat/KOK/1473", "puolue": "KOK", "tyyppi": "vaaliohjelma",    "vuosi": 2023 },
    { "id": "kok_periaate2018",   "url": f"{BASE}/pohtiva/ohjelmalistat/KOK/981",  "puolue": "KOK", "tyyppi": "periaateohjelma", "vuosi": 2018 },
    { "id": "ps_periaate2018",    "url": f"{BASE}/pohtiva/ohjelmalistat/PS/1302",  "puolue": "PS",  "tyyppi": "periaateohjelma", "vuosi": 2018 },
    { "id": "sdp_vaali2023",      "url": f"{BASE}/pohtiva/ohjelmalistat/SDP/1474", "puolue": "SDP", "tyyppi": "vaaliohjelma",    "vuosi": 2023 },
    { "id": "sdp_periaate2020",   "url": f"{BASE}/pohtiva/ohjelmalistat/SDP/1388", "puolue": "SDP", "tyyppi": "periaateohjelma", "vuosi": 2020 },
    { "id": "kesk_vaali2023",     "url": f"{BASE}/pohtiva/ohjelmalistat/KESK/1470","puolue": "KESK","tyyppi": "vaaliohjelma",    "vuosi": 2023 },
    { "id": "kesk_periaate2018",  "url": f"{BASE}/pohtiva/ohjelmalistat/KESK/1189","puolue": "KESK","tyyppi": "periaateohjelma", "vuosi": 2018 },
    { "id": "vihr_vaali2023",     "url": f"{BASE}/pohtiva/ohjelmalistat/VIHR/1485","puolue": "VIHR","tyyppi": "vaaliohjelma",    "vuosi": 2023 },
    { "id": "vihr_periaate2020",  "url": f"{BASE}/pohtiva/ohjelmalistat/VIHR/1387","puolue": "VIHR","tyyppi": "periaateohjelma", "vuosi": 2020 },
    { "id": "vas_vaali2023",      "url": f"{BASE}/pohtiva/ohjelmalistat/VAS/1472", "puolue": "VAS", "tyyppi": "vaaliohjelma",    "vuosi": 2023 },
    { "id": "vas_periaate2022",   "url": f"{BASE}/pohtiva/ohjelmalistat/VAS/1458", "puolue": "VAS", "tyyppi": "periaateohjelma", "vuosi": 2022 },
    { "id": "rkp_vaali2023",      "url": f"{BASE}/pohtiva/ohjelmalistat/SFP/1481", "puolue": "RKP", "tyyppi": "vaaliohjelma",    "vuosi": 2023 },
    { "id": "rkp_periaate2016",   "url": f"{BASE}/pohtiva/ohjelmalistat/SFP/926",  "puolue": "RKP", "tyyppi": "periaateohjelma", "vuosi": 2016 },
    { "id": "kd_vaali2023",       "url": f"{BASE}/pohtiva/ohjelmalistat/KD/1471",  "puolue": "KD",  "tyyppi": "vaaliohjelma",    "vuosi": 2023 },
    { "id": "kd_periaate2017",    "url": f"{BASE}/pohtiva/ohjelmalistat/KD/1185",  "puolue": "KD",  "tyyppi": "periaateohjelma", "vuosi": 2017 },
]

HEADERS = {"User-Agent": "Mozilla/5.0 (Politiikkapörssi-data-haku)"}

def hae_ohjelma(ohjelma: dict) -> dict | None:
    """Hakee yhden ohjelman Pohtivasta ja parsaa sen."""
    try:
        r = requests.get(ohjelma["url"], headers=HEADERS, timeout=15)
        r.raise_for_status()
        r.encoding = "utf-8"
        soup = BeautifulSoup(r.text, "html.parser")

        # Pohtivan ohjelmasisältö on article- tai main-tagissa
        # tai div.ohjelma-sisalto — kokeillaan järjestyksessä
        sisalto = (
            soup.find("article") or
            soup.find("main") or
            soup.find("div", class_="ohjelma") or
            soup.find("div", {"id": "content"})
        )

        if not sisalto:
            # Fallback: otetaan kaikki h1/h2/h3/p-tagit otsikon jälkeen
            sisalto = soup.find("body")

        # Parsaa rakenne: otsikot + kappaleet
        otsikko = ""
        h1 = soup.find("h1")
        if h1:
            otsikko = h1.get_text(strip=True)

        # Kerää lohkot: h2/h3 = otsikko, p/li = teksti
        lohkot = []
        if sisalto:
            for el in sisalto.find_all(["h1","h2","h3","h4","p","li","ol","ul"]):
                tag = el.name
                teksti = el.get_text(" ", strip=True)
                if not teksti or len(teksti) < 3:
                    continue
                # Ohita navigaatiolinkit
                if el.find("a") and len(teksti) < 60:
                    continue
                lohkot.append({"tag": tag, "teksti": teksti})

        return {
            "id":      ohjelma["id"],
            "puolue":  ohjelma["puolue"],
            "tyyppi":  ohjelma["tyyppi"],
            "vuosi":   ohjelma["vuosi"],
            "otsikko": otsikko,
            "lahde":   ohjelma["url"],
            "lohkot":  lohkot,
        }

    except Exception as e:
        print(f"  ❌ Virhe ({ohjelma['id']}): {e}")
        return None


def main():
    print(f"Haetaan {len(OHJELMAT)} ohjelmaa Pohtivasta...\n")

    # Tallenna myös indeksi
    indeksi = []

    for i, ohjelma in enumerate(OHJELMAT, 1):
        print(f"[{i}/{len(OHJELMAT)}] {ohjelma['id']} ... ", end="", flush=True)
        data = hae_ohjelma(ohjelma)

        if data:
            tiedosto = OUTPUT_DIR / f"{ohjelma['id']}.json"
            with open(tiedosto, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            lohkoja = len(data["lohkot"])
            koko = tiedosto.stat().st_size
            print(f"✅ {lohkoja} lohkoa, {koko//1000} kt")
            indeksi.append({
                "id":      data["id"],
                "puolue":  data["puolue"],
                "tyyppi":  data["tyyppi"],
                "vuosi":   data["vuosi"],
                "otsikko": data["otsikko"],
                "lahde":   data["lahde"],
            })
        else:
            print("❌ epäonnistui")

        time.sleep(0.5)  # Kohteliaisuustauko palvelimelle

    # Tallenna indeksi
    with open(OUTPUT_DIR / "index.json", "w", encoding="utf-8") as f:
        json.dump(indeksi, f, ensure_ascii=False, indent=2)

    print(f"\n✅ Valmis! {len(indeksi)}/{len(OHJELMAT)} ohjelmaa → {OUTPUT_DIR}/")
    print(f"   Muista lisätä ohjelmat_json/ Gitiin: git add ohjelmat_json/ && git commit -m 'Lisää ohjelmadat'")


if __name__ == "__main__":
    main()
