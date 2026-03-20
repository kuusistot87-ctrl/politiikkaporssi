#!/usr/bin/env python3
# Tarkistaa eduskunnan API:n sarakkeiden nimet
import json, urllib.request

def hae(url):
    req = urllib.request.Request(url, headers={"User-Agent":"Mozilla/5.0"})
    with urllib.request.urlopen(req, timeout=10) as r:
        return json.loads(r.read())

# Hae Orpo (pid=947) ja tulosta kaikki sarakkeet ja arvot
url = "https://avoindata.eduskunta.fi/api/v1/tables/MemberOfParliament/rows?perPage=10&page=0&columnName=personId&columnValue=947"
d = hae(url)
print("Sarakkeet:", d.get("columnNames"))
print(f"\nRivejä: {len(d.get('rowData',[]))}")
for row in d.get("rowData", []):
    e = dict(zip(d["columnNames"], row))
    print("\nRivi:")
    for k,v in e.items():
        if v: print(f"  {k}: {v}")
