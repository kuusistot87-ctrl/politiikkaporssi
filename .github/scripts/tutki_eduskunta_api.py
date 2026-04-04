"""
Tutki api.eduskunta.fi -rajapintaa
Aja: python tutki_eduskunta_api.py
"""

import urllib.request
import urllib.error
import json

BASE = "https://api.eduskunta.fi/v1"
BASE_OLD = "https://avoindata.eduskunta.fi/api/v1"

def get(url, label=""):
    print(f"\n{'='*60}")
    print(f"GET {url}")
    if label:
        print(f"    ({label})")
    try:
        req = urllib.request.Request(url, headers={
            "Accept": "application/json",
            "User-Agent": "Mozilla/5.0 (tutkimus)"
        })
        with urllib.request.urlopen(req, timeout=10) as r:
            raw = r.read().decode("utf-8")
            print(f"Status: {r.status}")
            try:
                data = json.loads(raw)
                # Näytä rakenne
                if isinstance(data, list):
                    print(f"→ Lista, {len(data)} riviä")
                    if data:
                        print(f"  Ensimmäinen alkio: {json.dumps(data[0], ensure_ascii=False, indent=2)[:500]}")
                elif isinstance(data, dict):
                    print(f"→ Objekti, avaimet: {list(data.keys())}")
                    print(json.dumps(data, ensure_ascii=False, indent=2)[:1000])
                else:
                    print(raw[:500])
            except:
                print(f"→ Raaka vastaus: {raw[:500]}")
    except urllib.error.HTTPError as e:
        print(f"HTTP {e.code}: {e.reason}")
        try:
            body = e.read().decode("utf-8")
            print(f"Body: {body[:300]}")
        except:
            pass
    except urllib.error.URLError as e:
        print(f"URLError: {e.reason}")
    except Exception as e:
        print(f"Virhe: {e}")

# ── 1. Uusi api.eduskunta.fi ──────────────────────────────────────
print("\n" + "█"*60)
print("█  UUSI: api.eduskunta.fi")
print("█"*60)

# Swagger / OpenAPI spec
get(f"{BASE}/", "Juuripolku")
get(f"{BASE}/openapi.json", "OpenAPI spec")
get(f"{BASE}/swagger.json", "Swagger spec")
get(f"{BASE}/docs", "Docs")

# Todennäköisiä endpointteja
get(f"{BASE}/members", "Kansanedustajat")
get(f"{BASE}/members/current", "Nykyiset edustajat")
get(f"{BASE}/votes", "Äänestykset")
get(f"{BASE}/votings", "Äänestykset (alt)")
get(f"{BASE}/sessions", "Täysistunnot")
get(f"{BASE}/members/1504", "Yksittäinen edustaja (Orpo personId?)")

# ── 2. Vanha avoindata.eduskunta.fi ──────────────────────────────
print("\n" + "█"*60)
print("█  VANHA: avoindata.eduskunta.fi")
print("█"*60)

get(f"{BASE_OLD}/tables/", "Kaikki taulut")
get(f"{BASE_OLD}/tables/SaliDBAanestysEdustaja/rows?page=0&perPage=3",
    "Äänestystulokset (3 riviä)")
get(f"{BASE_OLD}/tables/HetekaEdustajaHenkiloTiedot/rows?page=0&perPage=3",
    "Edustajien henkilötiedot")
get(f"{BASE_OLD}/tables/SaliDBAanestys/rows?page=0&perPage=3",
    "Äänestysmetadata")

print("\n\nValmis!")
