#!/usr/bin/env python3
"""
hae_wiki_kuvat.py
=================
Hakee Wikipedia-kuvat historiallisille kansanedustajille joilta puuttuu kuva.
Käyttää fi.wikipedia.org REST API:a.

Aja: python hae_wiki_kuvat.py

Vaatii internet-yhteyden. Voi kestää 10-20 minuuttia (1500+ hakua).
Keskeytä milloin tahansa Ctrl+C — jo haetut tallennetaan automaattisesti.
"""

import json, time, urllib.request, urllib.parse
from pathlib import Path

INDEX = Path("edustajat_json/index.json")

def hae_wiki_kuva(wiki_url):
    """Hakee kuvan Wikipedia-artikkelin URL:n perusteella."""
    if not wiki_url or "fi.wikipedia.org" not in wiki_url:
        return ""
    # Poimi artikkelin nimi URL:sta
    nimi = wiki_url.split("/wiki/")[-1]
    api_url = f"https://fi.wikipedia.org/api/rest_v1/page/summary/{nimi}"
    try:
        req = urllib.request.Request(
            api_url,
            headers={"User-Agent": "PolitiikkaporssiBot/1.0 (https://github.com/kuusistot87-ctrl/politiikkaporssi)"}
        )
        with urllib.request.urlopen(req, timeout=8) as r:
            data = json.loads(r.read())
            return (data.get("originalimage", {}).get("source", "") or
                    data.get("thumbnail", {}).get("source", ""))
    except:
        return ""

def main():
    with open(INDEX, encoding="utf-8") as f:
        data = json.load(f)

    # Etsi historialliset joilla on wiki-linkki mutta ei kuvaa
    kohteet = [
        e for e in data
        if not e.get("nykyinen")
        and not e.get("kuva")
        and e.get("wiki")
    ]

    print(f"Haetaan kuvia {len(kohteet)} historialliselle edustajalle...")
    print("(Keskeytä Ctrl+C milloin tahansa — tallentaa automaattisesti)\n")

    loydetty = 0
    ei_loydy = 0

    try:
        for i, e in enumerate(kohteet, 1):
            kuva = hae_wiki_kuva(e["wiki"])
            if kuva:
                e["kuva"] = kuva
                loydetty += 1
                if loydetty % 10 == 0:
                    print(f"  {i}/{len(kohteet)} — löydetty {loydetty} kuvaa ({e['nimi']})")
            else:
                ei_loydy += 1

            # Tallenna joka 50. hakemiston välein
            if i % 50 == 0:
                with open(INDEX, "w", encoding="utf-8") as f:
                    json.dump(data, f, ensure_ascii=False, separators=(",",":"))
                print(f"  [{i}/{len(kohteet)}] Tallennettu välitulos...")

            time.sleep(0.15)  # Kunnioita API:n rate limit

    except KeyboardInterrupt:
        print("\nKeskeytettiin — tallennetaan...")

    # Tallenna lopullinen tulos
    with open(INDEX, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, separators=(",",":"))

    print(f"\nValmis!")
    print(f"  Kuvia löydetty:   {loydetty}")
    print(f"  Ei löydetty:      {ei_loydy}")
    print(f"  Tallennettu:      {INDEX}")

if __name__ == "__main__":
    main()
