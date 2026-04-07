"""
hae_rahoitusepaselvyydet.py
Lataa VTV:n CSV ja laskee rahoitusepäselvyydet eduskuntavaalit 2023
"""

import csv
import json
import os
import urllib.request

CSV_URL = "https://www.vaalirahoitusvalvonta.fi/fi/index/vaalirahoitus/haetietoavaalirahoitusilmoituksista/tutkitietoaineistoja/eduskuntavaalit2023/E_VI_eduskuntavaalit2023.csv?dl=20231019_104538"

def hae_data():
    print("Ladataan CSV...")
    req = urllib.request.Request(CSV_URL, headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req, timeout=30) as resp:
        raw = resp.read().decode("utf-8-sig")

    # Poista lainausmerkit sarakkeiden nimistä
    rivit = raw.splitlines()
    print(f"Otsikkorivi: {rivit[0][:120]}")

    reader = csv.DictReader(rivit, delimiter=";")
    kaikki = list(reader)
    print(f"Rivejä: {len(kaikki)}")

    # Sarakkeiden nimet ovat muodossa "'Nimi'" -> strip kaikki
    def clean_key(k):
        return k.strip().strip("'").strip('"')

    def parse_num(s):
        if not s or s.strip().strip("'") == "":
            return None
        try:
            return float(s.strip().strip("'").replace(",", ".").replace("\xa0", "").replace(" ", ""))
        except:
            return None

    tulokset = []
    for row in kaikki:
        # Normalisoidaan avaimet
        r = {clean_key(k): v.strip().strip("'") for k, v in row.items()}

        etunimi  = r.get("Etunimet", "")
        sukunimi = r.get("Sukunimi", "")
        puolue   = r.get("Puolue", "")
        vaalipiiri = r.get("Vaalipiiri/Kunta", "")

        kulut    = parse_num(r.get("Vaalikampanjan kulut yhteensa", ""))
        rahoitus = parse_num(r.get("Vaalikampanjan rahoitus yhteensa", ""))

        if kulut is None or rahoitus is None:
            continue

        ero = round(rahoitus - kulut, 2)

        if abs(ero) > 1:
            tulokset.append({
                "nimi":       f"{etunimi} {sukunimi}".strip(),
                "sukunimi":   sukunimi,
                "puolue":     puolue,
                "vaalipiiri": vaalipiiri,
                "rahoitus":   round(rahoitus, 2),
                "kulut":      round(kulut, 2),
                "ero":        ero,
            })

    tulokset.sort(key=lambda x: abs(x["ero"]), reverse=True)

    os.makedirs("rahoitusepaselvyydet_json", exist_ok=True)
    outfile = "rahoitusepaselvyydet_json/eduskuntavaalit2023.json"
    with open(outfile, "w", encoding="utf-8") as f:
        json.dump(tulokset, f, ensure_ascii=False, indent=2)

    print(f"\nTallennettu {len(tulokset)} merkintaa -> {outfile}")
    print("\nTop 5:")
    for r in tulokset[:5]:
        print(f"  {r['nimi']} ({r['puolue']}): ero {r['ero']:+.2f}€")

if __name__ == "__main__":
    hae_data()
