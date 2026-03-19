import csv
import requests
import json
import time
import os

# Luodaan kansio tallennetuille tiedostoille, jos sitä ei ole
if not os.path.exists('edustajat_json'):
    os.makedirs('edustajat_json')

with open('results.csv', mode='r', encoding='utf-8') as file:
    reader = csv.DictReader(file)
    for row in reader:
        url = row['id']
        
        # Lisätään Accept-header, joka pyytää JSON-LD -muotoa (yleisin ldf.fi:ssä)
        headers = {
            'Accept': 'application/ld+json, application/json'
        }
        
        try:
            print(f"Haetaan: {row['label']}...")
            response = requests.get(url, headers=headers, timeout=10)
            
            # Tarkistetaan onko haku onnistunut
            if response.status_code == 200:
                # Varmistetaan, ettei vastaus ole tyhjä
                if response.text.strip():
                    data = response.json()
                    
                    # Puhdistetaan tiedostonimi (poistetaan erikoismerkit)
                    clean_name = "".join([c for c in row['label'] if c.isalnum() or c in (' ', '_')]).strip()
                    filename = f"edustajat_json/{clean_name}_{row['birth']}.json"
                    
                    with open(filename, 'w', encoding='utf-8') as f:
                        json.dump(data, f, ensure_ascii=False, indent=4)
                else:
                    print(f"Virhe: Palvelin palautti tyhjän vastauksen kohteelle {url}")
            else:
                print(f"Virhe: Palvelin vastasi koodilla {response.status_code}")
                
        except requests.exceptions.JSONDecodeError:
            print(f"Virhe: Kohde {url} ei palauttanut kelvollista JSONia.")
        except Exception as e:
            print(f"Tapahtui virhe: {e}")
        
        # Viive on tärkeä, jotta palvelin ei estä sinua
        time.sleep(1)