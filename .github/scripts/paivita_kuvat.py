#!/usr/bin/env python3
"""
paivita_kuvat.py
================
Lisää eduskunnan viralliset kuva-URLit nykyisille kansanedustajille index.json:ssa.

Aja: python paivita_kuvat.py

Kuva-URL kaava:
https://www.eduskunta.fi/FI/kansanedustajat/PublishingImages/Sukunimi-Etunimi-web-[id].jpg
"""

import json, re
from pathlib import Path

INDEX = Path("edustajat_json/index.json")

def puhdista(s):
    """Poistaa skandit ja erikoismerkit URL:ia varten."""
    return (s.replace("ä","a").replace("ö","o").replace("å","a")
             .replace("Ä","A").replace("Ö","O").replace("Å","A")
             .replace("é","e").replace("è","e").replace("ê","e")
             .replace("ü","u").replace("ú","u")
             .replace(" ","-"))

def hae_personid(eduskunta_url):
    """Hakee personId:n eduskunta.fi-linkistä: .../Sivut/1306.aspx → 1306"""
    if not eduskunta_url:
        return None
    m = re.search(r'/(\d+)\.aspx', eduskunta_url)
    return m.group(1) if m else None

def muodosta_kuvaurl(nimi, pid):
    """Muodostaa kuva-URL:n nimestä ja personId:stä.
    Eduskunnan kuvaformaatti: Sukunimi-Etunimi-web-[id].jpg
    Väliviivat säilytetään nimissä (Eeva-Johanna → Eeva-Johanna).
    Välilyönnit korvataan väliviivoilla.
    """
    if not pid:
        return None
    osat = nimi.strip().split()
    if len(osat) < 2:
        return None
    etunimi  = " ".join(osat[:-1])
    sukunimi = osat[-1]
    # Säilytä väliviiva, mutta puhdista skandit ja korvaa välilyönnit
    etu_puhdas  = puhdista(etunimi)   # "Eeva-Johanna" → "Eeva-Johanna"
    suku_puhdas = puhdista(sukunimi)  # "Aalto-Setälä" → "Aalto-Setala"
    return f"https://www.eduskunta.fi/FI/kansanedustajat/PublishingImages/{suku_puhdas}-{etu_puhdas}-web-{pid}.jpg"

def main():
    with open(INDEX, encoding="utf-8") as f:
        data = json.load(f)

    paivitetty = 0
    ei_pid     = 0

    for e in data:
        if not e.get("nykyinen"):
            continue
        pid = hae_personid(e.get("eduskunta",""))
        if not pid:
            ei_pid += 1
            continue
        kuva_url = muodosta_kuvaurl(e["nimi"], pid)
        if kuva_url:
            e["kuva"] = kuva_url
            paivitetty += 1

    with open(INDEX, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, separators=(",",":"))

    print(f"Valmis!")
    print(f"  Kuva-URL lisätty: {paivitetty} edustajalle")
    print(f"  Ei personId:tä:   {ei_pid} edustajaa")
    print(f"  Tallennettu:      {INDEX}")

    # Näytä muutama esimerkki
    print("\nEsimerkkejä:")
    for e in data:
        if e.get("nykyinen") and e.get("kuva","").startswith("https://www.eduskunta"):
            print(f"  {e['nimi']}: {e['kuva']}")
            break

if __name__ == "__main__":
    main()
