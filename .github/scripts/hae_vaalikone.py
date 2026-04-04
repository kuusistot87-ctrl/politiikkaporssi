"""
hae_vaalikone.py — Hakee 200 kansanedustajan UUID:t ja vaalikonevastaaukset
HS:n vaalikoneesta (eduskunta2023) Next.js JSON API:n kautta.

Käyttö:
    pip install requests
    python hae_vaalikone.py

Luo:
    vaalikone_json/yksilot/<uuid>.json   — jokaisen edustajan vastaukset
    vaalikone_json/uuid_hakemisto.json   — ehdokasnumero → UUID -kartta
    vaalikone_json/kysymykset.json       — kaikki 80 kysymystä

Kopioi tiedosto projektin juureen tai skriptit/-kansioon.
"""

import json
import time
import pathlib
import requests

# ── Konfiguraatio ────────────────────────────────────────────────
BUILD_ID   = "hEmB2U4uV1evmLmhv4JDE"
ELECTION   = "eduskunta2023"
BRAND      = "hs"
BASE_URL   = "https://vaalikone.fi"
API_BASE   = f"{BASE_URL}/_next/data/{BUILD_ID}/{ELECTION}/{BRAND}"

OUTPUT_DIR = pathlib.Path("vaalikone_json/yksilot")
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Politiikkapörssi-data-haku/1.0)",
    "Accept": "application/json",
    "Referer": f"{BASE_URL}/{ELECTION}/{BRAND}/ehdokkaat",
}

# Vaalipiirit (V-01 … V-13) — vaalikone käyttää näitä suoraan
VAALIPIIRIT = [
    "V-01","V-02","V-03","V-04","V-05","V-06","V-07",
    "V-08","V-09","V-10","V-11","V-12","V-13",
]

# Eduskuntapuolueiden UUID:t (next_data.json:sta)
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


def hae_json(url: str, nimi: str = "") -> dict | None:
    """Hakee JSON:n URL:sta, palauttaa None jos epäonnistuu."""
    try:
        r = requests.get(url, headers=HEADERS, timeout=20)
        r.raise_for_status()
        return r.json()
    except Exception as e:
        print(f"  ❌ {nimi}: {e}")
        return None


def hae_ehdokaslista() -> list[dict]:
    """
    Hakee kaikki ehdokkaat vaalipiireittäin Next.js API:sta.
    Palauttaa listan {uuid, nimi, puolue, vaalipiiri, ehdokasnumero}.
    """
    kaikki = []
    nahdut = set()

    # Kokeillaan ensin listasivua ilman vaalipiiriä
    url = f"{API_BASE}/candidates.json"
    data = hae_json(url, "ehdokaslista")
    if data:
        ehdokkaat = (data.get("pageProps", {})
                        .get("candidates") or
                     data.get("pageProps", {})
                        .get("initialCandidates") or [])
        print(f"  Päälista: {len(ehdokkaat)} ehdokasta")
        for e in ehdokkaat:
            uuid = e.get("id")
            if uuid and uuid not in nahdut:
                nahdut.add(uuid)
                kaikki.append(_muunna_ehdokas(e))

    # Haetaan vaalipiireittäin jotta saadaan kaikki
    for vp in VAALIPIIRIT:
        url = f"{API_BASE}/candidates.json?nominationArea={vp}"
        data = hae_json(url, f"vaalipiiri {vp}")
        if not data:
            time.sleep(1)
            continue
        pp = data.get("pageProps", {})
        ehdokkaat = (pp.get("candidates") or
                     pp.get("initialCandidates") or
                     pp.get("filteredCandidates") or [])
        uusia = 0
        for e in ehdokkaat:
            uuid = e.get("id")
            if uuid and uuid not in nahdut:
                nahdut.add(uuid)
                kaikki.append(_muunna_ehdokas(e))
                uusia += 1
        print(f"  {vp}: {len(ehdokkaat)} ehdokasta ({uusia} uutta)")
        time.sleep(0.3)

    return kaikki


def _muunna_ehdokas(e: dict) -> dict:
    return {
        "uuid":          e.get("id", ""),
        "etunimi":       e.get("firstName", ""),
        "sukunimi":      e.get("lastName", ""),
        "nimi":          f"{e.get('lastName', '')} {e.get('firstName', '')}",
        "puolue_uuid":   e.get("party", ""),
        "puolue":        EDUSKUNTAPUOLUEET.get(e.get("party", ""), ""),
        "ehdokasnumero": e.get("candidateNumber", ""),
        "vaalipiiri":    e.get("nominationArea", ""),
    }


def hae_vastaukset(uuid: str) -> dict | None:
    """Hakee yhden ehdokkaan vaalikonevastaaukset."""
    url = f"{API_BASE}/candidates/{uuid}.json"
    data = hae_json(url)
    if not data:
        return None

    pp = data.get("pageProps", {})
    candidate = pp.get("candidate", {})
    answers_raw = pp.get("answers", [])

    # Litistä vastaukset kysymysid → {vastaus, perustelu}
    vastaukset = {}
    for teema in answers_raw:
        for q in teema.get("questions", []):
            qid = q.get("questionId")
            if qid:
                vastaukset[str(qid)] = {
                    "vastaus":    q.get("answer"),       # 1-5
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


def tallenna_kysymykset(next_data_polku: str = "next_data.json"):
    """Tallentaa kysymykset erilliseen tiedostoon."""
    try:
        with open(next_data_polku, encoding="utf-8") as f:
            data = json.load(f)
        kysymykset = data["props"]["pageProps"]["questions"]
        teemat     = data["props"]["pageProps"]["themes"]
        teema_map  = {t["id"]: t["name"] for t in teemat}

        kysymys_lista = []
        for q in kysymykset:
            kysymys_lista.append({
                "id":         q["id"],
                "teksti":     q["text"],
                "teema_id":   q.get("theme"),
                "teema_nimi": teema_map.get(q.get("theme"), ""),
                "pakollinen": q.get("mandatory", False),
            })

        polku = pathlib.Path("vaalikone_json/kysymykset.json")
        with open(polku, "w", encoding="utf-8") as f:
            json.dump(kysymys_lista, f, ensure_ascii=False, indent=2)
        print(f"✅ {len(kysymys_lista)} kysymystä → {polku}")
        return kysymys_lista
    except Exception as e:
        print(f"⚠️  Kysymysten tallennus epäonnistui: {e}")
        return []


def main():
    print("=" * 60)
    print("HS Vaalikone 2023 — UUID & vastausten haku")
    print("=" * 60)

    # 1. Tallenna kysymykset
    print("\n[1/3] Tallennetaan kysymykset...")
    tallenna_kysymykset("next_data.json")

    # 2. Hae ehdokaslista
    print("\n[2/3] Haetaan ehdokaslista vaalipiireittäin...")
    ehdokkaat = hae_ehdokaslista()
    print(f"\n  Yhteensä: {len(ehdokkaat)} ehdokasta löydetty")

    # Suodata vain eduskuntapuolueet
    edust = [e for e in ehdokkaat if e["puolue"]]
    print(f"  Eduskuntapuolueet: {len(edust)} ehdokasta")

    # Tallenna UUID-hakemisto
    hakemisto = {e["uuid"]: e for e in edust}
    with open("vaalikone_json/uuid_hakemisto.json", "w", encoding="utf-8") as f:
        json.dump(hakemisto, f, ensure_ascii=False, indent=2)
    print(f"  → vaalikone_json/uuid_hakemisto.json ({len(hakemisto)} kpl)")

    # 3. Hae vastaukset
    print(f"\n[3/3] Haetaan vastaukset {len(edust)} ehdokkaalle...")
    print("  (Tämä kestää ~5-10 minuuttia, 0.5s tauko per ehdokas)\n")

    onnistui = 0
    epaonnistui = []

    for i, e in enumerate(edust, 1):
        uuid = e["uuid"]
        nimi = f"{e['sukunimi']} {e['etunimi']}"
        tiedosto = OUTPUT_DIR / f"{uuid}.json"

        # Ohita jo haetut
        if tiedosto.exists():
            print(f"  [{i:3}/{len(edust)}] ⏭  {nimi} (jo olemassa)")
            onnistui += 1
            continue

        print(f"  [{i:3}/{len(edust)}] ⬇  {nimi} ({e['puolue']}) ... ", end="", flush=True)
        data = hae_vastaukset(uuid)

        if data and data["vastaukset"]:
            with open(tiedosto, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            print(f"✅ {len(data['vastaukset'])} vastausta")
            onnistui += 1
        else:
            print("❌ epäonnistui")
            epaonnistui.append(nimi)

        time.sleep(0.5)

    # Yhteenveto
    print(f"\n{'=' * 60}")
    print(f"✅ Onnistui: {onnistui}/{len(edust)}")
    if epaonnistui:
        print(f"❌ Epäonnistui ({len(epaonnistui)} kpl):")
        for n in epaonnistui:
            print(f"   - {n}")

    print(f"\nSeuraavaksi:")
    print(f"  git add vaalikone_json/")
    print(f"  git commit -m 'Lisää vaalikone yksilödata'")
    print(f"  git push")


if __name__ == "__main__":
    main()
