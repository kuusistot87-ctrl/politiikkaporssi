#!/usr/bin/env python3
"""
hae_vaalikone_v3.py
-------------------
1. Rakentaa nimi->ehdokasnumero-hakemiston OM:n CSV:stä
2. Hakee jokaisen edustajan UUID:n HS:n vaalikoneesta
   hakemalla Googlesta: site:vaalikone.fi "{etunimi} {sukunimi}"
3. Hakee vastaukset __NEXT_DATA__:sta

Ajo: python skriptit/hae_vaalikone_v3.py
"""
import json, re, time, sys
from pathlib import Path
from urllib.parse import quote

try:
    import requests
    from bs4 import BeautifulSoup
except ImportError:
    print("pip install requests beautifulsoup4")
    sys.exit(1)

ROOT       = Path(__file__).parent.parent
INDEX_FILE = ROOT / "edustajat_json" / "index.json"
OM_CSV     = ROOT / "skriptit" / "ehd_maa.csv"  # OM:n ehdokasdata
OUT_DIR    = ROOT / "vaalikone_json"
OUT_DIR.mkdir(exist_ok=True)

BASE = "https://www.vaalikone.fi/eduskunta2023/hs"

session = requests.Session()
session.headers.update({
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
    "Accept-Language": "fi-FI,fi;q=0.9",
})

# Vaalipiirikoodi → HS:n nominationArea-koodi
VAALIPIIRI_KOODIT = {
    "01": "V-01", "02": "V-02", "03": "V-03", "04": "V-04",
    "05": "V-05", "06": "V-06", "07": "V-07", "08": "V-08",
    "09": "V-09", "10": "V-10", "11": "V-11", "12": "V-12",
    "13": "V-13",
}

def ascii_slug(nimi):
    k = {'ä':'a','ö':'o','å':'a','Ä':'A','Ö':'O','Å':'A'}
    return ''.join(k.get(c,c) for c in nimi).replace(' ','_')

def lataa_om_hakemisto():
    """Lataa OM:n CSV ja rakentaa nimi→{nro, vaalipiiri}-hakemiston."""
    if not OM_CSV.exists():
        print(f"OM CSV ei löydy: {OM_CSV}")
        print("Lataa tiedosto: https://tulospalvelu.vaalit.fi/EKV-2023/fi/ehd_maa.csv")
        print("ja tallenna skriptit/ehd_maa.csv")
        return {}

    hakemisto = {}
    with open(OM_CSV, encoding='latin-1') as f:
        for rivi in f:
            osat = rivi.split(';')
            if len(osat) < 20:
                continue
            ehdnro    = osat[14].strip().lstrip('0')  # esim. "0188" → "188"
            vaalipiiri = osat[1].strip()               # esim. "03"
            etunimi   = osat[17].strip()
            sukunimi  = osat[18].strip()
            if not etunimi or not sukunimi or not ehdnro:
                continue
            nimi_key = f"{etunimi} {sukunimi}".lower()
            hakemisto[nimi_key] = {
                "etunimi":    etunimi,
                "sukunimi":   sukunimi,
                "nro":        ehdnro,
                "vaalipiiri": vaalipiiri,
            }
    print(f"OM hakemisto: {len(hakemisto)} ehdokasta")
    return hakemisto

def etsi_uuid_ddg(etunimi, sukunimi):
    """Etsi UUID DuckDuckGo-haulla."""
    haku = f"{etunimi} {sukunimi} site:vaalikone.fi/eduskunta2023/hs/ehdokkaat"
    url  = f"https://html.duckduckgo.com/html/?q={quote(haku)}"
    try:
        r = session.get(url, timeout=15)
        uuids = re.findall(
            r'vaalikone\.fi/eduskunta2023/hs/ehdokkaat/([a-f0-9]{8}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{12})',
            r.text
        )
        return uuids[0] if uuids else None
    except:
        return None

def hae_vastaukset(uuid):
    """Hae ehdokkaan vastaukset __NEXT_DATA__:sta."""
    url = f"{BASE}/ehdokkaat/{uuid}"
    try:
        r = session.get(url, timeout=20)
        if not r.ok:
            return None
        soup = BeautifulSoup(r.text, 'html.parser')
        nd   = soup.find('script', id='__NEXT_DATA__')
        if not nd:
            return None
        data = json.loads(nd.string)
        pp   = data.get('props', {}).get('pageProps', {})

        answers_raw = pp.get('answers', [])
        candidate   = pp.get('candidate', {})

        vastaukset = []
        for teema in answers_raw:
            teema_nimi = teema.get('theme', {}).get('name', '')
            for q in teema.get('questions', []):
                arvo = q.get('answer')
                if arvo is None:
                    continue
                arvo_teksti = {
                    1: "Täysin eri mieltä",
                    2: "Jokseenkin eri mieltä",
                    3: "Ei samaa eikä eri mieltä",
                    4: "Jokseenkin samaa mieltä",
                    5: "Täysin samaa mieltä"
                }.get(arvo, str(arvo))
                vastaukset.append({
                    "teema":      teema_nimi,
                    "kysymys_id": q.get('questionId'),
                    "kysymys":    q.get('text', ''),
                    "arvo":       arvo,
                    "vastaus":    arvo_teksti,
                    "perustelu":  q.get('explanation', ''),
                })
        return {
            "candidate": candidate,
            "vastaukset": vastaukset,
        }
    except Exception as e:
        return None

# ── UUID-cache ──────────────────────────────────────────────────────
UUID_CACHE_FILE = OUT_DIR / "_uuid_cache.json"
uuid_cache = {}
if UUID_CACHE_FILE.exists():
    uuid_cache = json.loads(UUID_CACHE_FILE.read_text(encoding='utf-8'))

def tallenna_cache():
    UUID_CACHE_FILE.write_text(
        json.dumps(uuid_cache, ensure_ascii=False, indent=2), encoding='utf-8')

# ── PÄÄOHJELMA ──────────────────────────────────────────────────────
with open(INDEX_FILE, encoding='utf-8') as f:
    edustajat = json.load(f)

nykyiset   = [e for e in edustajat if e.get('nykyinen')]
om_hak     = lataa_om_hakemisto()

print(f"\nHaetaan vaalikonedata {len(nykyiset)} edustajalle...\n")

onnistui = 0
ei_loydy = 0
virhe    = 0
ei_uuid  = []

for i, edu in enumerate(nykyiset):
    nimi = edu.get('nimi', '')
    try:
        nimi = nimi.encode('latin-1').decode('utf-8')
    except:
        pass

    slug     = ascii_slug(nimi)
    tiedosto = OUT_DIR / f"{slug}.json"

    print(f"[{i+1:3d}/200] {nimi[:35]:<35} ", end="", flush=True)

    # Ohita jo haetut
    if tiedosto.exists():
        ex = json.loads(tiedosto.read_text(encoding='utf-8'))
        if ex.get('vastaukset'):
            print(f"✓ (ohitettu, {len(ex['vastaukset'])} vastausta)")
            onnistui += 1
            continue

    # Etsi UUID cachesta
    uuid = uuid_cache.get(nimi)

    if not uuid:
        # Etsi OM-hakemistosta ehdokkaan tiedot
        osat    = nimi.split()
        etunimi = osat[0]
        sukunimi = osat[-1]
        om_info = om_hak.get(f"{etunimi} {sukunimi}".lower())

        # Kokeile DuckDuckGo-hakua
        uuid = etsi_uuid_ddg(etunimi, sukunimi)
        if uuid:
            uuid_cache[nimi] = uuid
            tallenna_cache()
            print(f"[DDG] ", end="", flush=True)

    if not uuid:
        print("– UUID ei löydy")
        ei_loydy += 1
        ei_uuid.append(nimi)
        tiedosto.write_text(json.dumps({
            "nimi": nimi, "uuid": None, "vastaukset": []
        }, ensure_ascii=False), encoding='utf-8')
        time.sleep(1)
        continue

    # Hae vastaukset
    data = hae_vastaukset(uuid)
    if not data or not data.get('vastaukset'):
        print(f"✗ ei vastauksia (UUID: {uuid[:8]})")
        virhe += 1
        time.sleep(0.5)
        continue

    tulos = {
        "nimi":      nimi,
        "uuid":      uuid,
        "url":       f"{BASE}/ehdokkaat/{uuid}",
        "vastaukset": data['vastaukset'],
    }
    tiedosto.write_text(
        json.dumps(tulos, ensure_ascii=False, indent=2), encoding='utf-8')

    print(f"✓ {len(data['vastaukset'])} vastausta")
    onnistui += 1
    time.sleep(0.6)

print(f"\n{'─'*50}")
print(f"✓ Onnistui:  {onnistui}")
print(f"– Ei UUID:   {ei_loydy}")
print(f"✗ Virheitä:  {virhe}")
if ei_uuid:
    print(f"\nEi löytynyt ({len(ei_uuid)}):")
    for n in ei_uuid[:10]:
        print(f"  {n}")
print(f"\nSeuraavaksi:")
print(f"  git add vaalikone_json/")
print(f"  git commit -m 'Lisätään vaalikonedata'")
print(f"  git push")
