"""
tutki_api.py — Tutkii HS vaalikone API:n rakennetta
Aja ennen hae_vaalikone.py:tä
"""

import json
import requests

BUILD_ID = "hEmB2U4uV1evmLmhv4JDE"
ELECTION = "eduskunta2023"
BRAND    = "hs"
API_BASE = f"https://vaalikone.fi/_next/data/{BUILD_ID}/{ELECTION}/{BRAND}"

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)",
    "Accept": "application/json, */*",
    "Referer": f"https://vaalikone.fi/{ELECTION}/{BRAND}/ehdokkaat",
}

def hae(url):
    print(f"\n→ GET {url}")
    try:
        r = requests.get(url, headers=HEADERS, timeout=20)
        print(f"  Status: {r.status_code}")
        print(f"  Content-Type: {r.headers.get('Content-Type','?')}")
        if r.status_code == 200:
            try:
                data = r.json()
                pp = data.get("pageProps", {})
                print(f"  pageProps keys: {list(pp.keys())[:15]}")
                # Etsi listat
                for k, v in pp.items():
                    if isinstance(v, list):
                        print(f"  pageProps.{k}: list({len(v)})")
                        if len(v) > 0:
                            print(f"    [0] keys: {list(v[0].keys()) if isinstance(v[0], dict) else type(v[0])}")
                return data
            except:
                print(f"  Ei JSON. Vastaus: {r.text[:200]}")
        else:
            print(f"  Vastaus: {r.text[:200]}")
    except Exception as e:
        print(f"  VIRHE: {e}")
    return None

print("=" * 60)
print("Tutkitaan API-rakenne")
print("=" * 60)

# 1. Ehdokaslista ilman parametreja
hae(f"{API_BASE}/candidates.json")

# 2. Orpon sivu — tiedämme UUID:n
hae(f"{API_BASE}/candidates/d75d53d7-cdf9-407c-b3a6-e79369d18c55.json")

# 3. Kokeile eri parametrinimiä
for param in ["nominationArea", "district", "area", "vaalipiiri", "region"]:
    hae(f"{API_BASE}/candidates.json?{param}=V-01")

# 4. Kokeile myös vanhaa buildId:tä — saattaa olla vanhentunut
print("\n\n=== Kokeillaan hakea uusi buildId sivulta ===")
try:
    r = requests.get(
        "https://vaalikone.fi/eduskunta2023/hs/ehdokkaat",
        headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"},
        timeout=20
    )
    print(f"Status: {r.status_code}")
    # Etsi buildId HTML:stä
    import re
    match = re.search(r'"buildId":"([^"]+)"', r.text)
    if match:
        print(f"✅ Nykyinen buildId: {match.group(1)}")
        if match.group(1) != BUILD_ID:
            print(f"⚠️  VANHA buildId oli: {BUILD_ID}")
            print(f"   Päivitä hae_vaalikone.py:n BUILD_ID!")
    else:
        print("❌ buildId ei löydy HTML:stä")
        # Etsi __NEXT_DATA__
        nd = re.search(r'<script id="__NEXT_DATA__"[^>]*>(.*?)</script>', r.text, re.DOTALL)
        if nd:
            try:
                nd_data = json.loads(nd.group(1))
                print(f"buildId HTML:stä: {nd_data.get('buildId')}")
                pp = nd_data.get('props', {}).get('pageProps', {})
                print(f"pageProps keys: {list(pp.keys())[:10]}")
                # Tallenna
                with open("next_data_tuore.json", "w", encoding="utf-8") as f:
                    json.dump(nd_data, f, ensure_ascii=False, indent=2)
                print("→ Tallennettu next_data_tuore.json")
            except:
                print("JSON-parsinta epäonnistui")
except Exception as e:
    print(f"VIRHE: {e}")
