import json
import os
import shutil

# --- ASETUKSET ---
SOURCE_DIR = 'edustajat_json'  # Alkuperäinen kansio
TARGET_DIR = 'data_id_pohjainen' # Uusi siisti kansio
MISSING_ID_DIR = 'data_ei_idta'  # Varapaikka tiedostoille, joista ID puuttuu

# Luodaan kansiot jos niitä ei ole
for d in [TARGET_DIR, MISSING_ID_DIR]:
    if not os.path.exists(d):
        os.makedirs(d)

print(f"Aloitetaan tiedostojen käsittely kansiosta: {SOURCE_DIR}...")

files = [f for f in os.listdir(SOURCE_DIR) if f.endswith('.json')]
count = 0
errors = 0

for filename in files:
    source_path = os.path.join(SOURCE_DIR, filename)
    
    try:
        with open(source_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        # Etsitään ID eri mahdollisista paikoista (JSON-LD huomioiden)
        # 1. semparl:id (esim. 910222)
        # 2. @id (esim. people:p910222)
        raw_id = data.get('semparl:id')
        
        if not raw_id and '@id' in data:
            # Puhdistetaan "people:p910222" -> "910222"
            raw_id = data['@id'].split(':p')[-1]

        if raw_id:
            # Varmistetaan että ID on pelkkä numero/teksti ilman erikoismerkkejä
            new_filename = f"{raw_id}.json"
            target_path = os.path.join(TARGET_DIR, new_filename)
            
            # Kopioidaan tiedosto (shutil.copy säilyttää alkuperäisen)
            shutil.copy2(source_path, target_path)
            count += 1
        else:
            # Jos ID:tä ei löydy, siirretään talteen tarkistusta varten
            shutil.copy2(source_path, os.path.join(MISSING_ID_DIR, filename))
            errors += 1

    except Exception as e:
        print(f"Virhe tiedoston {filename} kohdalla: {e}")

print(f"\nVALMIS!")
print(f"- Onnistuneesti nimetyt: {count} kpl (löytyvät kansiosta: {TARGET_DIR})")
print(f"- Ilman ID:tä jääneet: {errors} kpl (löytyvät kansiosta: {MISSING_ID_DIR})")