#!/usr/bin/env python3
"""
hae_vaalikone_v2.py
-------------------
Hakee kansanedustajien vaalikonevastaaukset HS vaalikoneesta.
Strategia: hae jokaisen edustajan sivu hakemalla nimen perusteella
vaalikone.fi:n hakutoiminnosta, löydä UUID, hae __NEXT_DATA__.

Ajo: python skriptit/hae_vaalikone_v2.py
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
OUT_DIR    = ROOT / "vaalikone_json"
OUT_DIR.mkdir(exist_ok=True)

BASE = "https://www.vaalikone.fi/eduskunta2023/hs"

session = requests.Session()
session.headers.update({
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
    "Accept-Language": "fi-FI,fi;q=0.9",
    "Referer": BASE,
})

def ascii_slug(nimi):
    k = {'ä':'a','ö':'o','å':'a','Ä':'A','Ö':'O','Å':'A'}
    return ''.join(k.get(c,c) for c in nimi).replace(' ','_')

def etsi_uuid_hakusivulta(nimi):
    """Hae ehdokkaan UUID vaalikone.fi:n hakusivulta."""
    # HS vaalikone käyttää Next.js reititystä —
    # ehdokassivun URL on /ehdokkaat/{uuid}
    # Hae hakutulossivu joka palauttaa linkit ehdokkaisiin
    etunimi = nimi.split()[0]
    sukunimi = nimi.split()[-1]

    for hakutermi in [sukunimi, etunimi + " " + sukunimi]:
        url = f"{BASE}/ehdokkaat?search={quote(hakutermi)}"
        try:
            r = session.get(url, timeout=15)
            if not r.ok:
                continue
            soup = BeautifulSoup(r.text, 'html.parser')

            # Etsi linkit jotka osoittavat /ehdokkaat/{uuid}
            linkit = soup.find_all('a', href=re.compile(r'/ehdokkaat/[a-f0-9-]{36}'))
            for linkki in linkit:
                href = linkki.get('href', '')
                uuid = href.split('/')[-1]
                teksti = linkki.get_text(strip=True).lower()
                if (sukunimi.lower() in teksti or etunimi.lower() in teksti):
                    return uuid

            # Kokeile myös __NEXT_DATA__:sta
            next_data = soup.find('script', id='__NEXT_DATA__')
            if next_data:
                data = json.loads(next_data.string)
                ehdokkaat = (data.get('props', {})
                               .get('pageProps', {})
                               .get('candidates', []))
                for e in ehdokkaat:
                    fn = e.get('firstName', '').lower()
                    ln = e.get('lastName', '').lower()
                    if sukunimi.lower() in ln and etunimi.lower() in fn:
                        return e.get('id') or e.get('uuid')

        except Exception as ex:
            pass
        time.sleep(0.3)
    return None

def hae_vastaukset_uuid(uuid):
    """Hae ehdokkaan vaalikonevastaaukset UUID:n avulla."""
    url = f"{BASE}/ehdokkaat/{uuid}"
    try:
        r = session.get(url, timeout=20)
        if not r.ok:
            return None
        soup = BeautifulSoup(r.text, 'html.parser')
        next_data = soup.find('script', id='__NEXT_DATA__')
        if not next_data:
            return None
        data = json.loads(next_data.string)
        pp = data.get('props', {}).get('pageProps', {})
        return pp
    except Exception as e:
        return None

def parsi_vastaukset(pp):
    """Muunna pageProps-data siistiksi vastauslistaksi."""
    answers_raw = pp.get('answers', [])
    candidate   = pp.get('candidate', {})

    vastaukset = []
    for teema in answers_raw:
        teema_nimi = teema.get('theme', {}).get('name', '')
        for q in teema.get('questions', []):
            arvo = q.get('answer')
            if arvo is None:
                continue
            arvo_teksti = {1:"Täysin eri mieltä", 2:"Jokseenkin eri mieltä",
                           3:"Ei samaa eikä eri mieltä", 4:"Jokseenkin samaa mieltä",
                           5:"Täysin samaa mieltä"}.get(arvo, str(arvo))
            vastaukset.append({
                "teema":      teema_nimi,
                "kysymys_id": q.get('questionId'),
                "kysymys":    q.get('text', ''),
                "arvo":       arvo,
                "vastaus":    arvo_teksti,
                "perustelu":  q.get('explanation', ''),
            })
    return vastaukset

# ── UUID-hakemisto: tallennetaan löydetyt UUID:t ────────────────────
UUID_CACHE_FILE = OUT_DIR / "_uuid_cache.json"
uuid_cache = {}
if UUID_CACHE_FILE.exists():
    uuid_cache = json.loads(UUID_CACHE_FILE.read_text(encoding='utf-8'))

def tallenna_uuid_cache():
    UUID_CACHE_FILE.write_text(
        json.dumps(uuid_cache, ensure_ascii=False, indent=2), encoding='utf-8')

# ── PÄÄOHJELMA ──────────────────────────────────────────────────────

with open(INDEX_FILE, encoding='utf-8') as f:
    edustajat = json.load(f)

nykyiset = [e for e in edustajat if e.get('nykyinen')]
print(f"Haetaan vaalikonedata {len(nykyiset)} edustajalle...\n")

onnistui = 0
ei_loydy = 0
virhe    = 0
ei_loydy_lista = []

for i, edu in enumerate(nykyiset):
    nimi = edu.get('nimi', '')
    try:
        nimi = nimi.encode('latin-1').decode('utf-8')
    except:
        pass

    slug     = ascii_slug(nimi)
    tiedosto = OUT_DIR / f"{slug}.json"

    print(f"[{i+1:3d}/200] {nimi[:35]:<35} ", end="", flush=True)

    # Ohita jo haetut (jos vastauksia on)
    if tiedosto.exists():
        existing = json.loads(tiedosto.read_text(encoding='utf-8'))
        if existing.get('vastaukset'):
            print(f"✓ (ohitettu, {len(existing['vastaukset'])} vastausta)")
            onnistui += 1
            continue

    # Etsi UUID — ensin cachesta
    uuid = uuid_cache.get(nimi)

    if not uuid:
        uuid = etsi_uuid_hakusivulta(nimi)
        if uuid:
            uuid_cache[nimi] = uuid
            tallenna_uuid_cache()

    if not uuid:
        print("– UUID ei löydy")
        ei_loydy += 1
        ei_loydy_lista.append(nimi)
        tiedosto.write_text(json.dumps({
            "nimi": nimi, "uuid": None, "vastaukset": []
        }, ensure_ascii=False), encoding='utf-8')
        continue

    # Hae vastaukset
    pp = hae_vastaukset_uuid(uuid)
    if not pp:
        print(f"✗ sivun haku epäonnistui (UUID: {uuid[:8]})")
        virhe += 1
        continue

    vastaukset = parsi_vastaukset(pp)
    candidate  = pp.get('candidate', {})

    tulos = {
        "nimi":      nimi,
        "uuid":      uuid,
        "url":       f"{BASE}/ehdokkaat/{uuid}",
        "puolue_hs": candidate.get('party', {}).get('name', ''),
        "vastaukset": vastaukset,
    }

    tiedosto.write_text(
        json.dumps(tulos, ensure_ascii=False, indent=2),
        encoding='utf-8'
    )

    print(f"✓ {len(vastaukset)} vastausta")
    onnistui += 1
    time.sleep(0.4)

print(f"\n{'─'*50}")
print(f"✓ Onnistui:  {onnistui}")
print(f"– Ei UUID:   {ei_loydy}")
print(f"✗ Virheitä:  {virhe}")
if ei_loydy_lista:
    print(f"\nEi löytynyt ({len(ei_loydy_lista)}):")
    for n in ei_loydy_lista:
        print(f"  {n}")
print(f"\nSeuraavaksi:")
print(f"  git add vaalikone_json/")
print(f"  git commit -m \"Lisätään vaalikonedata\"")
print(f"  git push")
