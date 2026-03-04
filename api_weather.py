import requests
import pandas as pd 
import datetime

# ==========================================
# CONFIGURATION DE L'API
# ==========================================

# URL de base de l'API OpenDataSoft - Données SYNOP (stations météo françaises)
# Cette API publique fournit des données météorologiques essentielles
API_URL = "https://public.opendatasoft.com/api/explore/v2.1/catalog/datasets/donnees-synop-essentielles-omm/records"

# ==========================================
# FONCTION 1 : DONNÉES MÉTÉO PAR ANNÉE
# ==========================================

def get_meteo_data(year, limit=1000):
    """
    Récupère les données météo agrégées par ville pour une année donnée.
    
    Cette fonction interroge l'API pour obtenir la température moyenne de chaque ville
    sur l'année complète. Les données sont groupées par nom de ville.
    
    Paramètres:
        year (int/str): L'année pour filtrer les données (ex: 2022, 2021, etc.)
        limit (int): Nombre maximum de résultats à récupérer (par défaut 1000)
    
    Retour:
        DataFrame: Contient les colonnes Ville, lat, lon, Temperature
                   ou DataFrame vide en cas d'erreur
    """
    try:
        # Construction des paramètres de la requête API
        params = {
            "limit": limit,  # Limite le nombre de résultats
            
            # Filtre WHERE : sélectionne uniquement les données de l'année choisie
            # Syntaxe : date >= '2022-01-01' AND date <= '2022-12-31'
            "where": f"date >= date'{year}-01-01' AND date <= date'{year}-12-31'",
            
            # GROUP BY : agrège les données par nom de ville
            # Permet d'avoir une seule ligne par ville avec les moyennes
            "group_by": "nom",
            
            # SELECT : définit les colonnes à récupérer avec calculs
            # - nom as Ville : renomme la colonne "nom" en "Ville"
            # - avg(latitude) : moyenne des latitudes (car une ville peut avoir plusieurs stations)
            # - avg(tc) : température moyenne (tc = température Celsius)
            "select": "nom as Ville, avg(latitude) as lat, avg(longitude) as lon, avg(tc) as Temperature"
        }
        
        # Envoi de la requête GET vers l'API
        response = requests.get(API_URL, params=params)
        
        # Vérifie que la requête a réussi (code 200)
        # Lève une exception si erreur (404, 500, etc.)
        response.raise_for_status()
        
        # Conversion de la réponse JSON en dictionnaire Python
        data = response.json()
        
        # Vérification que la clé "results" existe dans la réponse
        if "results" in data:
            # Conversion du tableau JSON en DataFrame pandas
            df = pd.DataFrame(data["results"])
            return df
        else:
            # Si pas de résultats, retourne un DataFrame vide
            return pd.DataFrame()

    except Exception as e:
        # Gestion des erreurs (problème réseau, API indisponible, etc.)
        print(f"Erreur get_meteo_data: {e}")
        return pd.DataFrame()

# ==========================================
# FONCTION 2 : COMPARAISON RÉGIONALE MULTI-ANNÉES
# ==========================================

def get_region_comparison():
    """
    Récupère l'évolution des températures et précipitations par région et par année.
    
    Cette fonction permet de comparer les données météo entre différentes régions
    françaises sur plusieurs années (depuis 2018). Utilisée pour créer des graphiques
    d'évolution temporelle.
    
    Retour:
        DataFrame: Contient les colonnes Region, Annee, Temperature, Pluie
                   ou DataFrame vide en cas d'erreur
    """
    try:
        # Paramètres de la requête
        params = {
            "limit": 1000,
            
            # Filtre : données depuis 2018, uniquement les enregistrements avec région
            # nom_reg IS NOT NULL : exclut les stations sans région définie
            "where": "date >= date'2018-01-01' AND nom_reg IS NOT NULL",
            
            # Double groupement : par région ET par année
            # year(date) : fonction qui extrait l'année de la date
            "group_by": "nom_reg, year(date)",
            
            # Calcul des moyennes par groupe (région + année)
            # avg(tc) : température moyenne
            # avg(rr24) : précipitations moyennes sur 24h
            "select": "nom_reg, year(date) as Annee, avg(tc) as Temperature, avg(rr24) as Pluie"
        }
        
        response = requests.get(API_URL, params=params)
        
        # Force l'encodage UTF-8 pour gérer correctement les accents français
        response.encoding = "utf-8"
        response.raise_for_status()
        
        data = response.json()
        
        if "results" in data:
            df = pd.DataFrame(data["results"])
            
            # GESTION D'UN BUG DE L'API OpenDataSoft
            # Parfois l'API renvoie l'année dans 'year(date)' au lieu de 'Annee'
            # On vérifie et on corrige si nécessaire
            if 'year(date)' in df.columns and ('Annee' not in df.columns or df['Annee'].isna().all()):
                df['Annee'] = df['year(date)']
            
            # Renommage des colonnes pour avoir des noms propres et cohérents
            rename_map = {
                "nom_reg": "Region",
                "avg(tc)": "Temperature",
                "avg(rr24)": "Pluie"
            }
            df = df.rename(columns=rename_map)
            
            # Sélection des colonnes nécessaires
            cols_needed = ['Region', 'Annee', 'Temperature', 'Pluie']
            
            # Ne garde que les colonnes qui existent réellement
            # (sécurité en cas de changement de l'API)
            cols_final = [c for c in cols_needed if c in df.columns]
            df = df[cols_final]
            
            # Conversion de l'année en nombre entier
            # errors='coerce' : si conversion impossible, met NaN au lieu de planter
            if 'Annee' in df.columns:
                 df['Annee'] = pd.to_numeric(df['Annee'], errors='coerce')

            return df
        else:
            return pd.DataFrame()

    except Exception as e:
        print(f"Erreur get_region_comparison: {e}")
        return pd.DataFrame()

# ==========================================
# FONCTION 3 : FOCUS ZONE POITIERS
# ==========================================

def get_poitiers_data():
    """
    Récupère les observations météo brutes dans un rayon de 100km autour de Poitiers.
    
    Cette fonction utilise un filtre géographique pour sélectionner uniquement
    les stations proches de Poitiers. Utile pour une analyse locale détaillée.
    
    Retour:
        DataFrame: Contient les colonnes Ville, Date, Temperature, Pluie_24h
                   ou DataFrame vide en cas d'erreur
    """
    try:
        params = {
            "limit": 50,  # Limite à 50 résultats (suffisant pour une zone locale)
            
            # Tri par date décroissante pour avoir les données les plus récentes en premier
            "order_by": "date DESC",
            
            # Filtre géographique + temporel
            # within_distance : fonction spatiale de l'API
            #   - coordonnees : colonne de type géographique dans la base de données
            #   - geom'POINT(0.34 46.58)' : coordonnées GPS de Poitiers (longitude, latitude)
            #   - 100km : rayon de recherche
            # date >= 2021 : garde plusieurs années de données pour avoir assez de résultats
            "where": "within_distance(coordonnees, geom'POINT(0.34 46.58)', 100km) AND date >= date'2021-01-01'"
        }

        response = requests.get(API_URL, params=params)
        response.raise_for_status()
        data = response.json()
        
        if "results" in data:
            df = pd.DataFrame(data["results"])
            
            # Dictionnaire de renommage pour des noms de colonnes plus clairs
            rename_dict = {
                'tc': 'Temperature',  # tc = température Celsius
                'nom': 'Ville',
                'date': 'Date',
                'rr24': 'Pluie_24h'  # rr24 = cumul de pluie sur 24h
            }
            
            # Ne renomme que les colonnes qui existent dans le DataFrame
            # (sécurité si l'API change)
            cols_to_rename = {k: v for k, v in rename_dict.items() if k in df.columns}
            df = df.rename(columns=cols_to_rename)
            
            return df
        else:
            return pd.DataFrame()

    except Exception as e:
        print(f"Erreur get_poitiers_data: {e}")
        return pd.DataFrame()