#!/usr/bin/env python3
"""Tarkistaa mitä tietoja SaliDBAanestys-taulu sisältää"""
import urllib.request, json

API_BASE = "https://avoindata.eduskunta.fi/api/v1/tables"

def hae(url):
    req = urllib.request.Request(url, headers={"User-Agent": "test/1.0"})
    with urllib.request.urlopen(req, timeout=15) as r:
        return json.loads(r.read().decode("utf-8"))

# 1. Hae SaliDBAanestys-taulun rakenne
print("=== SaliDBAanestys rakenne ===")
data = hae(f"{API_BASE}/SaliDBAanestys/rows?page=0&perPage=2")
cols = data.get("columnNames", [])
print(f"Sarakkeet: {cols}")
for rivi in data.get("rowData", []):
    print(f"\nRivi: {dict(zip(cols, rivi))}")

# 2. Hae tietyllä AanestysId:llä (esim. Aalto-Setälän äänestyksistä)
# Ensin haetaan hänen äänestysId:nsä
print("\n=== Aalto-Setälän äänestysId:t ===")
data2 = hae(f"{API_BASE}/SaliDBAanestysEdustaja/rows?columnName=EdustajaHenkiloNumero&columnValue=1504&page=0&perPage=3")
cols2 = data2.get("columnNames", [])
for rivi in data2.get("rowData", []):
    d = dict(zip(cols2, rivi))
    aan_id = d.get("AanestysId","")
    print(f"\nAanestysId: {aan_id}")
    # Hae tämän äänestyksen tiedot
    data3 = hae(f"{API_BASE}/SaliDBAanestys/rows?columnName=AanestysId&columnValue={aan_id}&page=0&perPage=1")
    cols3 = data3.get("columnNames", [])
    rivit3 = data3.get("rowData", [])
    if rivit3:
        print(f"  {dict(zip(cols3, rivit3[0]))}")
