#!/usr/bin/env python3
"""
hae_vaalirahoitus.py
Hakee eduskuntavaalien 2023 ehdokaskohtaisen vaalirahoitusdatan.
Yhdistää edustajatietoihin nimen perusteella.
Lähde: Valtiontalouden tarkastusvirasto (VTV)
"""

import requests
import csv
import json
import io
import os
from datetime import datetime, timezone

BASE = "https://www.vaalirahoitusvalvonta.fi/fi/index/vaalirahoitus/haetietoavaalirahoitusilmoituksista/tutkitietoaineistoja"

TIEDOSTOT = {
    "eduskuntavaalit2023": {
        "ilmoitukset": f"{BASE}/eduskuntavaalit2023/E_VI_eduskuntavaalit2023.csv?dl=20231019_104538",
        "rahoitusrivit": f"{BASE}/eduskuntavaalit2023/RAHOITUSRIVIT_E_VI_eduskuntavaalit2023.csv?dl=20231019_104538",
        "jalki": f"{BASE}/eduskuntavaalit2023/E_JI_eduskuntavaalit2023.csv?dl=20260325_111727",
    }
}

def hae_csv(url):
    try:
        headers = {"User-Agent": "Mozilla/5.0 (compatible; PolitiikkaporssiBot/1.0)"}
        resp = requests.get(url, headers=headers, timeout=30)
        if resp.status_code == 200:
            try:
                return resp.content.decode("utf-8-sig")
            except:
                return resp.content.decode("latin-1")
        print(f"  HTTP {resp.status_code}: {url}")
        return None
    except Exception as e:
        print(f"  Virhe: {e}")
        return None

def lue_csv(teksti, erotin=";"):
    """Lukee CSV:n ja palauttaa list of dicts."""
    rivit = []
    reader = csv.reader(io.StringIO(teksti), delimiter=erotin, quotechar="'")
    otsikot = None
    for i, rivi in enumerate(reader):
        if i == 0:
            # Puhdista otsikot
            otsikot = [o.strip().strip("'\"") for o in rivi]
            continue
        if len(rivi) < 2:
            continue
        d = {otsikot[j]: rivi[j].strip().strip("'\"") for j in range(min(len(otsikot), len(rivi)))}
        rivit.append(d)
    return rivit, otsikot

def parsii_euro(s):
    if not s:
        return 0.0
    try:
        return float(s.replace(",", ".").replace(" ", ""))
    except:
        return 0.0

def normalisoi_nimi(etunimi, sukunimi):
    """Normalisoi nimi vertailua varten."""
    return f"{etunimi.strip().lower()} {sukunimi.strip().lower()}"

def main():
    nyt = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

    print("Haetaan eduskuntavaalit 2023 ilmoitukset...")
    ilm_teksti = hae_csv(TIEDOSTOT["eduskuntavaalit2023"]["ilmoitukset"])
    rah_teksti = hae_csv(TIEDOSTOT["eduskuntavaalit2023"]["rahoitusrivit"])

    if not ilm_teksti or not rah_teksti:
        print("VIRHE: Tiedostoja ei saatu!")
        return

    ilmoitukset, ilm_otsikot = lue_csv(ilm_teksti)
    rahoitusrivit, rah_otsikot = lue_csv(rah_teksti)

    print(f"  Ilmoituksia: {len(ilmoitukset)}")
    print(f"  Rahoitusrivejä: {len(rahoitusrivit)}")
    print(f"  Ilmoitusotsikot: {ilm_otsikot[:5]}")
    print(f"  Rahoitusotsikot: {rah_otsikot[:5]}")

    # Ryhmitä rahoitusrivit ehdokkaan nimellä
    tukijat_per_ehdokas = {}
    for r in rahoitusrivit:
        etunimi = r.get("Tuen saajan etunimet", "")
        sukunimi = r.get("Tuen saajan Sukunimi", "")
        avain = normalisoi_nimi(etunimi, sukunimi)
        if avain not in tukijat_per_ehdokas:
            tukijat_per_ehdokas[avain] = []
        summa = parsii_euro(r.get("Tuen maara", "0"))
        if summa > 0:
            tukijat_per_ehdokas[avain].append({
                "tukija": r.get("Tukija", ""),
                "ytunnus": r.get("Tukijan y-tunnus/yhdistysrekisterinumero jos on", ""),
                "etunimi": r.get("Tukijan etunimet", ""),
                "sukunimi": r.get("Tukijan sukunimi", ""),
                "kotikunta": r.get("Tukijan kotikunta jos on", ""),
                "summa": summa,
                "lahde": r.get("Tukilahteen lomakenumerot", ""),
            })

    # Rakenna ehdokasdata
    ehdokkaat = []
    for ilm in ilmoitukset:
        etunimi = ilm.get("Etunimet", "")
        sukunimi = ilm.get("Sukunimi", "")
        avain = normalisoi_nimi(etunimi, sukunimi)

        tukijat = sorted(
            tukijat_per_ehdokas.get(avain, []),
            key=lambda x: x["summa"],
            reverse=True
        )
        summa_tukijat = sum(t["summa"] for t in tukijat)

        kulut_yht = parsii_euro(ilm.get("Vaalikampanjan kulut yhteensa", "0"))
        rahoitus_yht = parsii_euro(ilm.get("Vaalikampanjan rahoitus yhteensa", "0"))
        omat_varat = parsii_euro(ilm.get("2.1 Rahoitus sisaltaa omia varoja yht", "0"))

        ehdokkaat.append({
            "etunimi": etunimi,
            "sukunimi": sukunimi,
            "nimi_avain": avain,
            "ehdokasnumero": ilm.get("Ehdokasnumero", ""),
            "vaalipiiri": ilm.get("Vaalipiiri/Kunta", ""),
            "puolue": ilm.get("Puolue", ""),
            "ammatti": ilm.get("Arvo/ammatti/tehtava", ""),
            "kulut_yhteensa": kulut_yht,
            "rahoitus_yhteensa": rahoitus_yht,
            "omat_varat": omat_varat,
            "tukijat_summa": summa_tukijat,
            "tukijat_lkm": len(tukijat),
            "top_tukijat": tukijat[:10],
        })

    # Järjestä rahoituksen mukaan
    ehdokkaat.sort(key=lambda x: x["rahoitus_yhteensa"], reverse=True)

    output = {
        "paivitetty": nyt,
        "lahde": "Valtiontalouden tarkastusvirasto (VTV)",
        "vaalit": "Eduskuntavaalit 2023",
        "ehdokkaita": len(ehdokkaat),
        "ehdokkaat": ehdokkaat,
    }

    os.makedirs("vaalirahoitus_json", exist_ok=True)
    polku = "vaalirahoitus_json/eduskuntavaalit2023.json"
    with open(polku, "w", encoding="utf-8") as f:
        json.dump(output, f, ensure_ascii=False, indent=2)

    print(f"\n✅ Tallennettu: {polku}")
    print(f"   Ehdokkaita: {len(ehdokkaat)}")
    print(f"   Eniten rahoitusta:")
    for e in ehdokkaat[:5]:
        print(f"     {e['etunimi']} {e['sukunimi']}: {e['rahoitus_yhteensa']:,.0f} €")

if __name__ == "__main__":
    main()
