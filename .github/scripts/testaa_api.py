#!/usr/bin/env python3
"""
Diagnostiikkaskripti — selvittää eduskunnan API:n oikeat sarakkeet.
Ajo: python skriptit/testaa_api.py
"""
import urllib.request
import urllib.parse
import json

API_BASE = "https://avoindata.eduskunta.fi/api/v1/tables"

def hae(url):
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "test/1.0"})
        with urllib.request.urlopen(req, timeout=15) as r:
            return json.loads(r.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        body = e.read().decode("utf-8", errors="replace")[:200]
        print(f"  400/virhne: {body}")
        return None
    except Exception as e:
        print(f"  VIRHE: {e}")
        return None

# 1. Hae yksi rivi ilman suodatusta — sarakkeet selviävät
print("=== 1. Taulun sarakkeet ===")
url = f"{API_BASE}/SaliDBAanestysEdustaja/rows?page=0&perPage=1"
print(f"URL: {url}")
data = hae(url)
if data:
    cols = data.get("columnNames", [])
    print(f"Sarakkeet: {cols}")
    rivit = data.get("rowData", [])
    if rivit and cols:
        print(f"Esim rivi: {dict(zip(cols, rivit[0]))}")

# 2. Kokeile eri sarakenimiä
print("\n=== 2. Sarakenimi-testit ===")
for col, val in [
    ("EdustajaHenkiloNro",    "800"),
    ("EdustajaHenkiloNumero", "800"),
    ("EdustajaNimi",          "Zyskowicz"),
    ("HenkiloNimi",           "Zyskowicz"),
    ("Edustaja",              "Zyskowicz"),
]:
    url = (f"{API_BASE}/SaliDBAanestysEdustaja/rows"
           f"?columnName={col}&columnValue={urllib.parse.quote(str(val))}&page=0&perPage=2")
    print(f"\n{col}={val}:")
    data = hae(url)
    if data:
        rivit = data.get("rowData", [])
        print(f"  → {len(rivit)} riviä ✓  sarakkeet: {data.get('columnNames',[])}")
