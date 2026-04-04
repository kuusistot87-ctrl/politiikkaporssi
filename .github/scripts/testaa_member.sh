#!/bin/bash
# Testaa MemberOfParliament-taulun oikea kyselytapa
BASE="https://avoindata.eduskunta.fi/api/v1"

echo "=== Testi 1: perPage=10 ilman muuta ==="
curl -s "$BASE/tables/MemberOfParliament/rows?page=0&perPage=10" | \
  python3 -c "import sys,json; d=json.loads(sys.stdin.read()); print('OK, rivejä:', d.get('rowCount'), 'hasMore:', d.get('hasMore'), 'avaimet:', list(d.keys()))" 2>&1

echo ""
echo "=== Testi 2: columnName=minister&columnValue=f (ei ministerit) ==="
curl -s "$BASE/tables/MemberOfParliament/rows?page=0&perPage=10&columnName=minister&columnValue=f" | \
  python3 -c "import sys,json; d=json.loads(sys.stdin.read()); print(d.get('message') or f'OK, rivejä: {d.get(\"rowCount\")}')" 2>&1

echo ""
echo "=== Testi 3: ilman sivutusta ==="
curl -s "$BASE/tables/MemberOfParliament/rows" | \
  python3 -c "import sys,json; d=json.loads(sys.stdin.read()); print(d.get('message') or f'OK rivejä: {d.get(\"rowCount\")}, hasMore: {d.get(\"hasMore\")}')" 2>&1

echo ""
echo "=== Testi 4: perPage=500 ==="
curl -s "$BASE/tables/MemberOfParliament/rows?page=0&perPage=500" | \
  python3 -c "import sys,json; d=json.loads(sys.stdin.read()); print(d.get('message') or f'OK rivejä: {d.get(\"rowCount\")}, hasMore: {d.get(\"hasMore\")}')" 2>&1

echo ""
echo "=== Testi 5: pkStartValue ==="
curl -s "$BASE/tables/MemberOfParliament/rows?pkStartValue=0&perPage=200" | \
  python3 -c "import sys,json; d=json.loads(sys.stdin.read()); print(d.get('message') or f'OK rivejä: {d.get(\"rowCount\")}, pkLastValue: {d.get(\"pkLastValue\")}')" 2>&1

echo ""
echo "=== Testi 6: Hae yksi henkilö personId:llä ==="
curl -s "$BASE/tables/MemberOfParliament/rows?columnName=personId&columnValue=1504" | \
  python3 -c "
import sys,json
d=json.loads(sys.stdin.read())
if 'message' in d:
    print('Virhe:', d['message'])
else:
    for r in d['rowData']:
        row = dict(zip(d['columnNames'], r))
        print(f'personId={row[\"personId\"]} nimi={row[\"firstname\"]} {row[\"lastname\"]} puolue={row[\"party\"]}')
" 2>&1

echo ""
echo "=== Testi 7: Hae Orpo nimellä ==="
curl -s "$BASE/tables/MemberOfParliament/rows?columnName=lastname&columnValue=Orpo" | \
  python3 -c "
import sys,json
d=json.loads(sys.stdin.read())
if 'message' in d:
    print('Virhe:', d['message'])
else:
    print(f'Rivejä: {d[\"rowCount\"]}')
    for r in d['rowData']:
        row = dict(zip(d['columnNames'], r))
        print(f'  personId={row[\"personId\"]} {row[\"firstname\"]} {row[\"lastname\"]} puolue={row[\"party\"]}')
" 2>&1

echo "=== VALMIS ==="
