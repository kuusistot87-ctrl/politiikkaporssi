"""
hae_vaalikone2.py — Hakee UUID:t ehdokasnumeroiden kautta
ja lataa vaalikonevastaaukset.

Strategia:
  1. Lue ehdokasnumerot.json (edustajat + vaalipiirit)
  2. Hae jokaisen edustajan ehdokassivu HTML:nä
  3. Parsaa __NEXT_DATA__:sta UUID ja vastaukset suoraan
  4. Tallenna vaalikone_json/yksilot/<uuid>.json

Käyttö:
    pip install requests
    python skriptit/hae_vaalikone2.py
"""

import json
import re
import time
import pathlib
import requests

OUTPUT_DIR  = pathlib.Path("vaalikone_json/yksilot")
HAKEMISTO_F = pathlib.Path("vaalikone_json/uuid_hakemisto.json")
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

BASE_URL = "https://vaalikone.fi"
ELECTION = "eduskunta2023"
BRAND    = "hs"

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:120.0) Gecko/20100101 Firefox/120.0",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "fi-FI,fi;q=0.9",
    "Referer": f"{BASE_URL}/{ELECTION}/{BRAND}/ehdokkaat",
}

EDUSKUNTAPUOLUEET = {
    "9eedf280-8da6-4d74-9ee4-7f8d3b87cd90": "KESK",
    "2ef3060b-602f-43a9-8008-ae8a0c427426": "KOK",
    "72b23234-d423-4bfa-a463-1f6649df0e0a": "KD",
    "8c1e3917-0920-4893-9597-1e8860371f1c": "PS",
    "f4bbeb67-3b0a-4b81-9606-0f192652e91b": "RKP",
    "aaa152ae-1854-48ef-986e-ea764ed56a24": "SDP",
    "c2fa2f51-0d85-46d0-ab42-89593f70d92b": "VAS",
    "231dead0-c733-4991-a8c0-0d511e11cdc4": "VIHR",
    "b782e02f-0fdf-42e5-be9c-53cdd89615c4": "LIIK",
}

# Vaalipiirikoodi → URL-polku vaalikoneessa
VAALIPIIRI_URL = {
    "Helsingin":         "V-01",
    "Uudenmaan":         "V-02",
    "Varsinais-Suomen":  "V-03",
    "Satakunnan":        "V-04",
    "Ahvenanmaan":       "V-05",
    "Hämeen":            "V-06",
    "Pirkanmaan":        "V-07",
    "Kaakkois-Suomen":   "V-08",
    "Savo-Karjalan":     "V-09",
    "Vaasan":            "V-10",
    "Keski-Suomen":      "V-11",
    "Oulun":             "V-12",
    "Lapin":             "V-13",
}


def hae_ehdokasnumerot() -> list[dict]:
    """Lataa ehdokasnumerot.json tai muodostaa listan edustajat_json:sta."""
    # Kokeile ensin ehdokasnumerot.json
    polku = pathlib.Path("skriptit/ehdokasnumerot.json")
    if polku.exists():
        with open(polku, encoding="utf-8") as f:
            data = json.load(f)
        print(f"  Luettu {len(data)} edustajaa ehdokasnumerot.json:sta")
        return data

    # Fallback: lue edustajat_json/index.json
    polku2 = pathlib.Path("edustajat_json/index.json")
    if polku2.exists():
        with open(polku2, encoding="utf-8") as f:
            data = json.load(f)
        # Muodosta lista
        tulos = []
        for m in data:
            if m.get("nykyinen"):
                tulos.append({
                    "nimi": m.get("nimi", ""),
                    "puolue": m.get("puolue", ""),
                    "vaalipiiri": m.get("vaalipiiri", ""),
                    "ehdokasnumero": m.get("ehdokasnumero", ""),
                })
        print(f"  Muodostettu {len(tulos)} edustajaa edustajat_json/index.json:sta")
        return tulos

    print("❌ Ei löydy ehdokasnumerot.json eikä edustajat_json/index.json")
    return []


def hae_ehdokassivu_uuid(nimi: str, vaalipiiri: str, ehdokasnumero) -> tuple[str, dict] | tuple[None, None]:
    """
    Hakee ehdokassivun HTML:n ja parsaa sieltä UUID:n ja vastaukset.
    Yrittää ensin ehdokasnumerolla, sitten nimellä.
    """
    # Muodosta ehdokassivun URL vaalipiirin kautta
    # URL-muoto: /eduskunta2023/hs/ehdokkaat?vaalipiiri=V-03&numero=188
    # TAI suoraan: /eduskunta2023/hs/ehdokkaat/<uuid> jos UUID tunnetaan

    # Hae listasivulta ja parsaa UUID ehdokasnumerolla
    vp_koodi = None
    for avain, koodi in VAALIPIIRI_URL.items():
        if avain in vaalipiiri:
            vp_koodi = koodi
            break

    if not vp_koodi:
        print(f"    ⚠️  Vaalipiiri ei tunnistettu: {vaalipiiri}")
        return None, None

    # Hae vaalipiirin ehdokaslista HTML:nä ja parsaa __NEXT_DATA__
    url = f"{BASE_URL}/{ELECTION}/{BRAND}/ehdokkaat?vaalipiiri={vp_koodi}"
    try:
        r = requests.get(url, headers=HEADERS, timeout=20)
        if r.status_code != 200:
            return None, None

        # Parsaa __NEXT_DATA__
        match = re.search(r'<script id="__NEXT_DATA__"[^>]*>(.*?)</script>', r.text, re.DOTALL)
        if not match:
            return None, None

        nd = json.loads(match.group(1))
        pp = nd.get("props", {}).get("pageProps", {})

        # Etsi ehdokkaat — saattaa olla eri avaimessa
        ehdokkaat = (pp.get("candidates") or
                     pp.get("initialCandidates") or
                     pp.get("filteredCandidates") or [])

        if not ehdokkaat:
            # Kokeile build ID -pohjaista API:a
            build_id = nd.get("buildId")
            if build_id:
                api_url = f"{BASE_URL}/_next/data/{build_id}/{ELECTION}/{BRAND}/candidates.json"
                r2 = requests.get(api_url, headers={**HEADERS, "Accept": "application/json"}, timeout=20)
                if r2.status_code == 200:
                    pp2 = r2.json().get("pageProps", {})
                    ehdokkaat = (pp2.get("candidates") or
                                 pp2.get("initialCandidates") or [])

        # Etsi oikea ehdokas numerolla tai nimellä
        for e in ehdokkaat:
            if (str(e.get("candidateNumber", "")) == str(ehdokasnumero) or
                e.get("lastName", "").lower() in nimi.lower()):
                return e.get("id"), e

    except Exception as ex:
        print(f"    Virhe: {ex}")

    return None, None


def hae_vastaukset_uuid(uuid: str, build_id: str) -> dict | None:
    """Hakee vastaukset UUID:lla Next.js API:sta."""
    url = f"{BASE_URL}/_next/data/{build_id}/{ELECTION}/{BRAND}/candidates/{uuid}.json"
    try:
        r = requests.get(url, headers={**HEADERS, "Accept": "application/json"}, timeout=20)
        if r.status_code != 200:
            return None
        pp = r.json().get("pageProps", {})
        candidate = pp.get("candidate", {})
        answers_raw = pp.get("answers", [])

        vastaukset = {}
        for teema in answers_raw:
            for q in teema.get("questions", []):
                qid = q.get("questionId")
                if qid:
                    vastaukset[str(qid)] = {
                        "vastaus":    q.get("answer"),
                        "perustelu":  q.get("explanation", ""),
                        "teema_id":   teema.get("theme", {}).get("id"),
                        "teema_nimi": teema.get("theme", {}).get("name", ""),
                        "kysymys":    q.get("text", ""),
                    }

        return {
            "uuid":          uuid,
            "etunimi":       candidate.get("firstName", ""),
            "sukunimi":      candidate.get("lastName", ""),
            "puolue_uuid":   candidate.get("party", ""),
            "puolue":        EDUSKUNTAPUOLUEET.get(candidate.get("party", ""), ""),
            "ehdokasnumero": candidate.get("candidateNumber", ""),
            "vaalipiiri":    candidate.get("nominationArea", ""),
            "arvot":         candidate.get("values", {}),
            "vastaukset":    vastaukset,
        }
    except Exception as e:
        print(f"    Virhe vastausten haussa: {e}")
        return None


def hae_build_id() -> str:
    """Hakee nykyisen buildId:n sivulta."""
    try:
        r = requests.get(f"{BASE_URL}/{ELECTION}/{BRAND}/ehdokkaat", headers=HEADERS, timeout=20)
        match = re.search(r'"buildId":"([^"]+)"', r.text)
        if match:
            return match.group(1)
    except:
        pass
    return "hEmB2U4uV1evmLmhv4JDE"  # fallback


def hae_suoraan_html(nimi: str, vaalipiiri: str, ehdokasnumero, build_id: str) -> dict | None:
    """
    Strategia 2: Hae vaalipiirin sivu, parsaa kaikki ehdokkaat,
    etsi oikea ehdokasnumerolla.
    """
    vp_koodi = None
    for avain, koodi in VAALIPIIRI_URL.items():
        if avain in vaalipiiri:
            vp_koodi = koodi
            break
    if not vp_koodi:
        return None

    # Hae vaalipiirisivu HTML:nä
    url = f"{BASE_URL}/{ELECTION}/{BRAND}/ehdokkaat"
    params = {"vaalipiiri": vp_koodi}
    try:
        r = requests.get(url, headers=HEADERS, params=params, timeout=20)
        nd_match = re.search(r'<script id="__NEXT_DATA__"[^>]*>(.*?)</script>', r.text, re.DOTALL)
        if not nd_match:
            return None
        nd = json.loads(nd_match.group(1))
        pp = nd.get("props", {}).get("pageProps", {})

        # Kaikki mahdolliset listat
        for key in ["candidates", "initialCandidates", "filteredCandidates", "allCandidates"]:
            ehdokkaat = pp.get(key, [])
            if ehdokkaat:
                print(f"    Löydetty {len(ehdokkaat)} ehdokasta avaimella '{key}'")
                for e in ehdokkaat:
                    if str(e.get("candidateNumber","")) == str(ehdokasnumero):
                        return e
                break

        print(f"    pageProps-avaimet: {[k for k in pp.keys() if not isinstance(pp[k], (dict,)) or len(str(pp[k])) < 100]}")

    except Exception as e:
        print(f"    HTML-haku virhe: {e}")
    return None


def main():
    print("=" * 60)
    print("HS Vaalikone — UUID-haku ehdokasnumeroiden kautta")
    print("=" * 60)

    # 1. Hae nykyinen buildId
    print("\n[1/4] Haetaan buildId...")
    build_id = hae_build_id()
    print(f"  buildId: {build_id}")

    # 2. Lataa edustajat
    print("\n[2/4] Ladataan edustajat...")
    edustajat = hae_ehdokasnumerot()
    if not edustajat:
        print("❌ Ei edustajia. Lopetetaan.")
        return

    # Lataa olemassa oleva hakemisto
    uuid_hakemisto = {}
    if HAKEMISTO_F.exists():
        with open(HAKEMISTO_F, encoding="utf-8") as f:
            uuid_hakemisto = json.load(f)
        print(f"  Olemassa olevassa hakemistossa: {len(uuid_hakemisto)} UUID:ta")

    # 3. Testaa ensin Orpolla (tiedämme UUID:n)
    print("\n[3/4] Testataan Orpon UUID:lla...")
    testi = hae_vastaukset_uuid("d75d53d7-cdf9-407c-b3a6-e79369d18c55", build_id)
    if testi:
        print(f"  ✅ Orpo: {len(testi['vastaukset'])} vastausta")
    else:
        print("  ❌ Orpon testaus epäonnistui!")
        return

    # 4. Hae kaikki edustajat
    print(f"\n[4/4] Haetaan {len(edustajat)} edustajan UUID:t ja vastaukset...")
    print("  Strategia: vaalipiirisivu HTML → ehdokasnumero → UUID → vastaukset\n")

    onnistui = 0
    epaonnistui = []
    
    # Kerää vaalipiirikohtaiset ehdokkaat ensin (1 haku/vaalipiiri)
    vp_ehdokkaat = {}  # vp_koodi → {nro: uuid}

    print("  Haetaan UUID:t vaalipiireittäin...")
    for vp_nimi, vp_koodi in VAALIPIIRI_URL.items():
        url = f"{BASE_URL}/{ELECTION}/{BRAND}/ehdokkaat"
        try:
            r = requests.get(url, headers=HEADERS, 
                           params={"vaalipiiri": vp_koodi}, timeout=20)
            nd_match = re.search(r'<script id="__NEXT_DATA__"[^>]*>(.*?)</script>', 
                                r.text, re.DOTALL)
            if not nd_match:
                print(f"  {vp_koodi}: ❌ ei __NEXT_DATA__")
                continue
                
            nd = json.loads(nd_match.group(1))
            pp = nd.get("props", {}).get("pageProps", {})
            
            ehdokkaat = []
            for key in ["candidates","initialCandidates","filteredCandidates","allCandidates"]:
                if pp.get(key):
                    ehdokkaat = pp[key]
                    break
            
            vp_ehdokkaat[vp_koodi] = {
                str(e.get("candidateNumber","")): e.get("id","")
                for e in ehdokkaat if e.get("id")
            }
            print(f"  {vp_koodi} ({vp_nimi}): {len(ehdokkaat)} ehdokasta, "
                  f"{len(vp_ehdokkaat[vp_koodi])} UUID:ta")
            time.sleep(0.5)
            
        except Exception as e:
            print(f"  {vp_koodi}: ❌ {e}")

    # Jos vaalipiirihaku ei tuottanut tuloksia, kokeile API:a
    total_uuid = sum(len(v) for v in vp_ehdokkaat.values())
    print(f"\n  Yhteensä {total_uuid} UUID:ta kerätty vaalipiireistä")

    if total_uuid == 0:
        print("\n  ⚠️  Vaalipiirihaku ei tuottanut UUID:ta.")
        print("  Kokeillaan hakea suoraan API:sta puolueittain...")
        
        for puolue_uuid, puolue_nimi in EDUSKUNTAPUOLUEET.items():
            api_url = (f"{BASE_URL}/_next/data/{build_id}/{ELECTION}/{BRAND}"
                      f"/candidates.json?party={puolue_uuid}")
            r = requests.get(api_url, 
                           headers={**HEADERS, "Accept": "application/json"}, 
                           timeout=20)
            if r.status_code == 200:
                pp = r.json().get("pageProps", {})
                for key in ["candidates","initialCandidates"]:
                    if pp.get(key):
                        print(f"  {puolue_nimi}: {len(pp[key])} ehdokasta avaimella '{key}'")
            time.sleep(0.3)
        
        print("\n  ❌ UUID:jen haku epäonnistui. Sivusto saattaa ladata ehdokkaat")
        print("     pelkästään JS:llä — tarvitaan Playwright-ratkaisu.")
        print("     Aja: pip install playwright && playwright install chromium")
        return

    # Hae vastaukset UUID:lla
    print(f"\n  Haetaan vastaukset {len(edustajat)} edustajalle...")
    
    for i, edustaja in enumerate(edustajat, 1):
        nimi = edustaja.get("nimi", "")
        nro  = str(edustaja.get("ehdokasnumero", ""))
        vp   = edustaja.get("vaalipiiri", "")

        # Etsi UUID vaalipiirikohtaisesta hakemistosta
        uuid = None
        for vp_avain, vp_koodi in VAALIPIIRI_URL.items():
            if vp_avain in vp:
                uuid = vp_ehdokkaat.get(vp_koodi, {}).get(nro)
                break

        if not uuid:
            # Kokeile kaikista vaalipiireistä
            for vp_data in vp_ehdokkaat.values():
                if nro in vp_data:
                    uuid = vp_data[nro]
                    break

        tiedosto = OUTPUT_DIR / f"{uuid}.json" if uuid else None

        print(f"  [{i:3}/{len(edustajat)}] {nimi[:25]:25} nro:{nro:5}", end=" ")

        if not uuid:
            print("❌ UUID ei löydy")
            epaonnistui.append(nimi)
            continue

        if tiedosto and tiedosto.exists():
            print(f"⏭  (jo haettu: {uuid[:8]}...)")
            onnistui += 1
            uuid_hakemisto[uuid] = {"nimi": nimi, "nro": nro, "vp": vp}
            continue

        data = hae_vastaukset_uuid(uuid, build_id)
        if data and data["vastaukset"]:
            with open(tiedosto, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            uuid_hakemisto[uuid] = {"nimi": nimi, "nro": nro, "vp": vp}
            print(f"✅ {uuid[:8]}... {len(data['vastaukset'])}kys")
            onnistui += 1
        else:
            print(f"❌ vastaukset tyhjät")
            epaonnistui.append(nimi)

        time.sleep(0.4)

    # Tallenna hakemisto
    with open(HAKEMISTO_F, "w", encoding="utf-8") as f:
        json.dump(uuid_hakemisto, f, ensure_ascii=False, indent=2)

    print(f"\n{'=' * 60}")
    print(f"✅ Onnistui: {onnistui}/{len(edustajat)}")
    if epaonnistui:
        print(f"❌ Epäonnistui ({len(epaonnistui)}):")
        for n in epaonnistui[:10]:
            print(f"   - {n}")
    print(f"\ngit add vaalikone_json/ && git commit -m 'Vaalikone yksilödata' && git push")


if __name__ == "__main__":
    main()
