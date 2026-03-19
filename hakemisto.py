import json
import os

SOURCE_DIR = 'data_id_pohjainen'
HAKEMISTO_FILE = 'edustaja_haku.json'

hakemisto = []

print("Luodaan hakemistoa...")

for filename in os.listdir(SOURCE_DIR):
    if filename.endswith('.json'):
        path = os.path.join(SOURCE_DIR, filename)
        try:
            with open(path, 'r', encoding='utf-8') as f:
                d = json.load(f)
                
                # Poimitaan nimi ja ID
                nimi = d.get('skos:prefLabel', {}).get('@value') or d.get('skos:hiddenLabel', {}).get('@value', "Tuntematon")
                edustaja_id = filename.replace('.json', '') # esim. 102
                
                hakemisto.append({
                    "id": edustaja_id,
                    "nimi": nimi
                })
        except:
            continue

# Tallennetaan aakkosjärjestyksessä
hakemisto.sort(key=lambda x: x['nimi'])

with open(HAKEMISTO_FILE, 'w', encoding='utf-8') as f:
    json.dump(hakemisto, f, ensure_ascii=False, indent=2)

print(f"VALMIS! Luotu {len(hakemisto)} nimen hakemisto tiedostoon {HAKEMISTO_FILE}")