import os
import json
import pandas as pd
from api_weather import get_meteo_data, get_region_comparison, get_poitiers_data

def export_to_json():
    # Créer le dossier data s'il n'existe pas
    os.makedirs('data', exist_ok=True)
    
    print("Exportation des données météo en cours...")
    
    # 1. Données Météo par année (Prenons 2023 par exemple)
    print("Récupération des données météo pour 2023...")
    df_meteo = get_meteo_data(2023, limit=1000)
    if not df_meteo.empty:
        df_meteo.to_json('data/meteo_2023.json', orient='records', force_ascii=False)
        print("- meteo_2023.json généré avec succès.")
    else:
        print("- Erreur ou aucune donnée pour meteo 2023.")

    # 2. Comparaison Régionale Multi-Années
    print("\nRécupération de la comparaison régionale...")
    df_region = get_region_comparison()
    if not df_region.empty:
        df_region.to_json('data/region_comparison.json', orient='records', force_ascii=False)
        print("- region_comparison.json généré avec succès.")
    else:
        print("- Erreur ou aucune donnée pour la comparaison régionale.")

    # 3. Focus Zone Poitiers
    print("\nRécupération des données pour Poitiers...")
    df_poitiers = get_poitiers_data()
    if not df_poitiers.empty:
        # Assurez-vous que les dates sont formatées comme des chaînes si elles sont datetime
        if 'Date' in df_poitiers.columns and pd.api.types.is_datetime64_any_dtype(df_poitiers['Date']):
            df_poitiers['Date'] = df_poitiers['Date'].dt.strftime('%Y-%m-%d %H:%M:%S')
        df_poitiers.to_json('data/poitiers_data.json', orient='records', force_ascii=False)
        print("- poitiers_data.json généré avec succès.")
    else:
        print("- Erreur ou aucune donnée pour Poitiers.")
        
    print("\n✅ Exportation terminée !")

if __name__ == "__main__":
    export_to_json()
