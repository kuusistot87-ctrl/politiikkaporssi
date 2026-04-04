#!/bin/bash
# Tutki api.eduskunta.fi -rajapintaa
# Aja: bash skriptit/tutki_eduskunta_api.sh

BASE="https://api.eduskunta.fi/v1"
BASE_OLD="https://avoindata.eduskunta.fi/api/v1"

get() {
  local url="$1"
  local label="$2"
  echo ""
  echo "============================================================"
  echo "GET $url"
  [ -n "$label" ] && echo "    ($label)"
  echo "------------------------------------------------------------"
  curl -s -o /tmp/api_resp.txt -w "HTTP %{http_code}" \
    -H "Accept: application/json" \
    -H "User-Agent: Mozilla/5.0 (tutkimus)" \
    --max-time 10 \
    "$url" | tee /tmp/api_status.txt
  echo ""
  # Näytä vastauksen alku
  head -c 800 /tmp/api_resp.txt | python3 -c "
import sys, json
raw = sys.stdin.read()
try:
    d = json.loads(raw)
    if isinstance(d, list):
        print(f'→ Lista, {len(d)} alkiota')
        if d: print(json.dumps(d[0], ensure_ascii=False, indent=2)[:600])
    elif isinstance(d, dict):
        print(f'→ Objekti, avaimet: {list(d.keys())}')
        print(json.dumps(d, ensure_ascii=False, indent=2)[:600])
except:
    print(raw[:600])
" 2>/dev/null || head -c 600 /tmp/api_resp.txt
  echo ""
}

echo "████████████████████████████████████████████████████████████"
echo "█  UUSI: api.eduskunta.fi/v1"
echo "████████████████████████████████████████████████████████████"

get "$BASE/"                        "Juuripolku"
get "$BASE/openapi.json"            "OpenAPI spec"
get "$BASE/swagger.json"            "Swagger"
get "$BASE/docs"                    "Docs"
get "$BASE/members"                 "Kansanedustajat"
get "$BASE/members/current"         "Nykyiset edustajat"
get "$BASE/members/1504"            "Yksittäinen edustaja"
get "$BASE/votes"                   "Äänestykset"
get "$BASE/votings"                 "Äänestykset alt"
get "$BASE/sessions"                "Täysistunnot"
get "$BASE/committees"              "Valiokunnat"
get "$BASE/parties"                 "Puolueet"

echo ""
echo "████████████████████████████████████████████████████████████"
echo "█  VANHA: avoindata.eduskunta.fi/api/v1"
echo "████████████████████████████████████████████████████████████"

get "$BASE_OLD/tables/"             "Kaikki taulut"
get "$BASE_OLD/tables/SaliDBAanestysEdustaja/rows?page=0&perPage=3" \
                                    "Äänestystulokset"
get "$BASE_OLD/tables/HetekaEdustajaHenkiloTiedot/rows?page=0&perPage=3" \
                                    "Edustajien henkilötiedot"
get "$BASE_OLD/tables/SaliDBAanestys/rows?page=0&perPage=3" \
                                    "Äänestysmetadata"

echo ""
echo "████████████  VALMIS  ████████████"
