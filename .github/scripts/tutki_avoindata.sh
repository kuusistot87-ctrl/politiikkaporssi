#!/bin/bash
# Tutki avoindata.eduskunta.fi tarkemmin
# Aja: bash skriptit/tutki_avoindata.sh

BASE="https://avoindata.eduskunta.fi/api/v1"

get() {
  local url="$1"
  local label="$2"
  echo ""
  echo "============================================================"
  echo "$label"
  echo "GET $url"
  echo "------------------------------------------------------------"
  curl -s -H "Accept: application/json" --max-time 10 "$url" | \
  python3 -c "
import sys, json
raw = sys.stdin.read()
try:
    d = json.loads(raw)
    if isinstance(d, list):
        print(f'Lista, {len(d)} alkiota:')
        for item in d:
            print(f'  - {item}')
    elif isinstance(d, dict):
        keys = list(d.keys())
        print(f'Avaimet: {keys}')
        if 'columnNames' in d:
            print(f'Sarakkeet: {d[\"columnNames\"]}')
        if 'rowData' in d:
            print(f'Rivejä: {d[\"rowCount\"]} (hasMore={d[\"hasMore\"]})')
            for r in d['rowData'][:3]:
                print(f'  {r}')
        else:
            print(json.dumps(d, ensure_ascii=False, indent=2)[:800])
except Exception as e:
    print(f'Parse error: {e}')
    print(raw[:400])
" 2>/dev/null
  echo ""
}

echo "████  KAIKKI 19 TAULUA  ████"
get "$BASE/tables/" "Taulujen lista"

echo ""
echo "████  ÄÄNESTYKSET  ████"

get "$BASE/tables/SaliDBAanestys/rows?page=0&perPage=3" \
    "SaliDBAanestys — äänestysmetadata"

get "$BASE/tables/SaliDBAanestysEdustaja/rows?page=0&perPage=3" \
    "SaliDBAanestysEdustaja — edustajien äänet"

# Kuinka monta äänestystä yhteensä?
echo ""
echo "████  ÄÄNESTYKSIÄ YHTEENSÄ?  ████"
curl -s "$BASE/tables/SaliDBAanestys/rows?page=0&perPage=1" | \
  python3 -c "
import sys,json
d=json.loads(sys.stdin.read())
print(f'hasMore={d[\"hasMore\"]}, pkLastValue={d.get(\"pkLastValue\")}, eka AanestysId={d[\"rowData\"][0][0] if d[\"rowData\"] else \"?\"}')"

echo ""
echo "████  UUSIMMAT ÄÄNESTYKSET (viimeisin sivu)  ████"
# Haetaan suurella page-numerolla tai käänteisessä järjestyksessä
get "$BASE/tables/SaliDBAanestys/rows?page=0&perPage=3&columnName=IstuntoVPVuosi&columnValue=2025" \
    "Äänestykset 2025"

get "$BASE/tables/SaliDBAanestys/rows?page=0&perPage=3&columnName=IstuntoVPVuosi&columnValue=2024" \
    "Äänestykset 2024"

echo ""
echo "████  EDUSTAJATIEDOT  ████"

# Kokeillaan eri taulun nimiä edustajille
for taulu in \
  "MemberOfParliament" \
  "EdustajaHenkiloTiedot" \
  "Edustaja" \
  "Member" \
  "HenkiloTiedot" \
  "VaskiHenkiloTiedot" \
  "SaliDBEdustaja"
do
  code=$(curl -s -o /tmp/t.txt -w "%{http_code}" "$BASE/tables/$taulu/rows?page=0&perPage=1")
  if [ "$code" = "200" ]; then
    echo "✅ LÖYTYI: $taulu"
    cat /tmp/t.txt | python3 -c "
import sys,json
d=json.loads(sys.stdin.read())
print(f'  Sarakkeet: {d[\"columnNames\"]}')
if d['rowData']: print(f'  Esimerkki: {d[\"rowData\"][0]}')" 2>/dev/null
  else
    echo "❌ $taulu → $code"
  fi
done

echo ""
echo "████  ÄÄNESTYSTULOS ORPON PERSONID:llä  ████"
# EdustajaHenkiloNumero=1504 on Orpo?
get "$BASE/tables/SaliDBAanestysEdustaja/rows?page=0&perPage=5&columnName=EdustajaHenkiloNumero&columnValue=1504" \
    "Orpon äänet (henkilönumero 1504)"

echo ""
echo "████  VALMIS  ████"
