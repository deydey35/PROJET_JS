import streamlit as st
import pandas as pd
import folium
from streamlit_folium import st_folium
import seaborn as sns
import matplotlib.pyplot as plt
import os
import time
from geopy.geocoders import Nominatim
from math import radians, sin, cos, sqrt, asin
import plotly.express as px
import webscrapping

# ==========================================
# CONFIGURATION INITIALE DE LA PAGE
# ==========================================

# Configuration du titre et du layout de la page Streamlit
st.set_page_config(page_title="Dashboard SAE - Tesla & Météo", layout="wide")

# ==========================================
# IMPORT DES FONCTIONS API MÉTÉO
# ==========================================

# Tentative d'import du fichier api_weather.py
try:
    from api_weather import get_meteo_data, get_poitiers_data, get_region_comparison
except ImportError:
    # Si le fichier n'existe pas, on affiche une erreur
    st.error("⚠️ Le fichier 'api_weather.py' est introuvable ou contient des erreurs.")
    # Définition de fonctions vides pour éviter que le programme crash
    def get_meteo_data(year, limit=100): return pd.DataFrame()
    def get_poitiers_data(): return pd.DataFrame()
    def get_region_comparison(): return pd.DataFrame()

# ==========================================
# CRÉATION DES ONGLETS PRINCIPAUX
# ==========================================

st.title("📊 Projet Collecte de données Web")
# Création de 2 onglets : un pour Tesla, un pour la météo
tab_tesla, tab_meteo = st.tabs(["🚗 Superchargeurs Tesla", "🌤️ Météo API"])

# ==========================================
# VÉRIFICATION DU SCRIPT DE SCRAPING
# ==========================================

# Vérification que le fichier webscrapping.py existe
try:
    import webscrapping
except ImportError:
    st.error("⚠️ Le fichier 'webscrapping.py' est introuvable.")
    st.stop()  # Arrête l'exécution si le fichier manque

# ==========================================
# DICTIONNAIRE DES DÉPARTEMENTS FRANÇAIS
# ==========================================

# Mapping code postal -> nom du département
# Permet d'afficher le nom complet à partir des 2 premiers chiffres du code postal
DEPARTEMENTS = {
    '01': 'Ain', '02': 'Aisne', '03': 'Allier', '04': 'Alpes-de-Haute-Provence', '05': 'Hautes-Alpes',
    '06': 'Alpes-Maritimes', '07': 'Ardèche', '08': 'Ardennes', '09': 'Ariège', '10': 'Aube',
    '11': 'Aude', '12': 'Aveyron', '13': 'Bouches-du-Rhône', '14': 'Calvados', '15': 'Cantal',
    '16': 'Charente', '17': 'Charente-Maritime', '18': 'Cher', '19': 'Corrèze', '2A': 'Corse-du-Sud',
    '2B': 'Haute-Corse', '21': 'Côte-d\'Or', '22': 'Côtes-d\'Armor', '23': 'Creuse', '24': 'Dordogne',
    '25': 'Doubs', '26': 'Drôme', '27': 'Eure', '28': 'Eure-et-Loir', '29': 'Finistère',
    '30': 'Gard', '31': 'Haute-Garonne', '32': 'Gers', '33': 'Gironde', '34': 'Hérault',
    '35': 'Ille-et-Vilaine', '36': 'Indre', '37': 'Indre-et-Loire', '38': 'Isère', '39': 'Jura',
    '40': 'Landes', '41': 'Loir-et-Cher', '42': 'Loire', '43': 'Haute-Loire', '44': 'Loire-Atlantique',
    '45': 'Loiret', '46': 'Lot', '47': 'Lot-et-Garonne', '48': 'Lozère', '49': 'Maine-et-Loire',
    '50': 'Manche', '51': 'Marne', '52': 'Haute-Marne', '53': 'Mayenne', '54': 'Meurthe-et-Moselle',
    '55': 'Meuse', '56': 'Morbihan', '57': 'Moselle', '58': 'Nièvre', '59': 'Nord',
    '60': 'Oise', '61': 'Orne', '62': 'Pas-de-Calais', '63': 'Puy-de-Dôme', '64': 'Pyrénées-Atlantiques',
    '65': 'Hautes-Pyrénées', '66': 'Pyrénées-Orientales', '67': 'Bas-Rhin', '68': 'Haut-Rhin',
    '69': 'Rhône', '70': 'Haute-Saône', '71': 'Saône-et-Loire', '72': 'Sarthe', '73': 'Savoie',
    '74': 'Haute-Savoie', '75': 'Paris', '76': 'Seine-Maritime', '77': 'Seine-et-Marne', '78': 'Yvelines',
    '79': 'Deux-Sèvres', '80': 'Somme', '81': 'Tarn', '82': 'Tarn-et-Garonne', '83': 'Var',
    '84': 'Vaucluse', '85': 'Vendée', '86': 'Vienne', '87': 'Haute-Vienne', '88': 'Vosges',
    '89': 'Yonne', '90': 'Territoire de Belfort', '91': 'Essonne', '92': 'Hauts-de-Seine',
    '93': 'Seine-Saint-Denis', '94': 'Val-de-Marne', '95': 'Val-d\'Oise'
}

# ==========================================
# ONGLET 1 : SUPERCHARGEURS TESLA
# ==========================================

with tab_tesla:
    # --- BARRE LATÉRALE : RECHERCHE D'ITINÉRAIRE ---
    with st.sidebar:
        st.header("🔍 Itinéraire")
        # Champ de saisie pour la ville de l'utilisateur
        user_city = st.text_input("Votre ville :") 
        
        # Variable pour stocker les coordonnées GPS de l'utilisateur
        user_coords = None
        if user_city:
            # Initialisation du géolocalisateur Nominatim (OpenStreetMap)
            geolocator = Nominatim(user_agent="tesla_dashboard_app_v2")
            try:
                # Recherche des coordonnées en ajoutant ", France" pour préciser
                location = geolocator.geocode(f"{user_city}, France")
                if location:
                    # Récupération des coordonnées (latitude, longitude)
                    user_coords = (location.latitude, location.longitude)
                else:
                    st.warning("Ville introuvable.")
            except:
                st.warning("Service de géolocalisation indisponible.")

    # --- CHARGEMENT DU FICHIER CSV ---
    # Récupération du chemin du dossier contenant ce script
    current_dir = os.path.dirname(os.path.abspath(__file__))
    csv_file = os.path.join(current_dir, "resultat_tesla_france_final.csv")

    # Initialisation d'un DataFrame vide
    df = pd.DataFrame()
    # Vérification que le fichier CSV existe
    if os.path.exists(csv_file):
        try:
            # Lecture du fichier CSV
            df = pd.read_csv(csv_file)
        except Exception:
            df = pd.DataFrame()

    # --- TRAITEMENT DES DONNÉES ---
    if not df.empty:
        try:
            # NETTOYAGE ET TRANSFORMATION DES DONNÉES
            
            # Extraction de la puissance en kW (conversion en nombre)
            # Exemple : "250 kW" -> 250
            df['kW_int'] = df['Puissance'].astype(str).str.extract(r'(\d+)').astype(float).fillna(0)
            
            # Séparation des coordonnées GPS (format "lat,lon")
            lat_lon = df['GPS'].str.split(',', expand=True)
            df['latitude'] = pd.to_numeric(lat_lon[0])
            df['longitude'] = pd.to_numeric(lat_lon[1])
            
            # Fonction pour obtenir le nom du département à partir du code postal
            def get_nom_departement(cp):
                if pd.isna(cp): return "Inconnu"
                # Extraction des 2 premiers caractères du code postal
                code = str(cp)[:2]
                # Recherche dans le dictionnaire
                return DEPARTEMENTS.get(code, f"Dept {code}")
            
            # Ajout d'une colonne avec le nom du département
            df['Nom_Departement'] = df['Code_Postal'].apply(get_nom_departement)

            # --- CALCUL DE LA STATION LA PLUS PROCHE ---
            if user_coords:
                # Fonction de calcul de distance GPS (formule de Haversine)
                # Permet de calculer la distance entre 2 points sur une sphère
                def haversine(lon1, lat1, lon2, lat2):
                    # Conversion des degrés en radians
                    lon1, lat1, lon2, lat2 = map(radians, [lon1, lat1, lon2, lat2])
                    # Calcul des différences
                    dlon = lon2 - lon1 
                    dlat = lat2 - lat1 
                    # Formule de Haversine
                    a = sin(dlat/2)**2 + cos(lat1) * cos(lat2) * sin(dlon/2)**2
                    c = 2 * asin(sqrt(a)) 
                    r = 6371  # Rayon de la Terre en km
                    return c * r
                
                # Calcul de la distance pour chaque station
                df['distance_user'] = df.apply(
                    lambda row: haversine(user_coords[1], user_coords[0], row['longitude'], row['latitude']), 
                    axis=1
                )
                
                # Sélection de la station la plus proche
                nearest = df.sort_values('distance_user').iloc[0]
                
                # Affichage dans la barre latérale
                with st.sidebar:
                    st.success(f"📌 **{nearest['Nom']}**")
                    st.write(f"Distance : **{nearest['distance_user']:.1f} km**")
                    st.write(f"Puissance : **{nearest['Puissance']}**")
                    # Bouton pour lancer Google Maps avec l'itinéraire
                    st.link_button(
                        "🚗 Y aller (Maps)", 
                        f"https://www.google.com/maps/dir/?api=1&destination={nearest['latitude']},{nearest['longitude']}"
                    )

            # --- INDICATEURS CLÉS (KPI) ---
            st.markdown("### 📊 Indicateurs Clés")
            # Création de 4 colonnes pour afficher les métriques
            k1, k2, k3, k4 = st.columns(4)
            k1.metric("Total Stations", len(df))
            # Comptage des superchargeurs ultra-rapides (≥250 kW)
            k2.metric("Superchargeurs Rapides", len(df[df['kW_int'] >= 250]))
            # Calcul de la puissance moyenne
            k3.metric("Puissance Moyenne", f"{int(df['kW_int'].mean())} kW")
            # Nombre de départements différents
            k4.metric("Départements couverts", df['Nom_Departement'].nunique())

            # --- GRAPHIQUES ---
            st.markdown("---")
            c1, c2 = st.columns(2)
            
            # GRAPHIQUE 1 : Camembert des types de chargeurs
            with c1:
                st.markdown("#### ⚡ Répartition par Puissance")
                
                # Fonction de catégorisation de la puissance
                def cat_puissance(kw):
                    if kw >= 250: return "V3/V4 (Ultra-Rapide)"
                    elif kw >= 150: return "V2 (Rapide)"
                    else: return "Urbain / Lent"
                
                # Ajout d'une colonne Type
                df['Type'] = df['kW_int'].apply(cat_puissance)
                # Création du graphique en camembert
                fig_pie = px.pie(df, names='Type', color_discrete_sequence=['green', 'orange', 'red'])
                st.plotly_chart(fig_pie, use_container_width=True)
            
            # GRAPHIQUE 2 : Top 5 des départements
            with c2:
                st.markdown("#### 🇫🇷 Top 5 Départements")
                # Comptage des stations par département
                top_dep = df['Nom_Departement'].value_counts().head(5).reset_index()
                # Renommage des colonnes pour plus de clarté
                top_dep.columns = ['Département', 'Nombre de Stations']
                # Index qui commence à 1 au lieu de 0
                top_dep.index = top_dep.index + 1
                st.dataframe(top_dep, use_container_width=True)

            # --- CARTE INTERACTIVE ---
            st.markdown("---")
            st.subheader("🗺️ Carte du Réseau Tesla")
            
            # Légende HTML personnalisée avec style inline
            st.markdown("""
            <div style="
                background-color: white; 
                color: black; 
                padding: 10px; 
                border-radius: 5px; 
                border: 1px solid #ccc;
                margin-bottom: 10px;
                display: inline-block;
            ">
                <strong>Légende :</strong> 
                <span style='color: green;'>●</span> Ultra-Rapide (≥250kW) &nbsp;
                <span style='color: orange;'>●</span> Rapide (150kW) &nbsp;
                <span style='color: red;'>●</span> Lent
            </div>
            """, unsafe_allow_html=True)

            # Création de la carte centrée sur la France
            m = folium.Map(location=[46.6, 1.9], zoom_start=6)
            
            # Ajout d'un marqueur pour chaque station
            for _, row in df.iterrows():
                if pd.notnull(row['latitude']):
                    kw = row['kW_int']
                    
                    # Choix de la couleur et de l'icône selon la puissance
                    if kw >= 250:
                        color, icon = "green", "bolt"
                    elif kw >= 150:
                        color, icon = "orange", "charging-station"
                    else:
                        color, icon = "red", "plug"
                    
                    # Ajout du marqueur sur la carte
                    folium.Marker(
                        [row['latitude'], row['longitude']],
                        popup=f"<b>{row['Nom']}</b><br>{row['Puissance']}<br>{row['Ville']}",
                        icon=folium.Icon(color=color, icon=icon, prefix="fa")
                    ).add_to(m)
            
            # Affichage de la carte dans Streamlit
            st_folium(m, width=None, height=500, key="map_tesla")
            
            # --- TABLEAU DES DONNÉES BRUTES ---
            st.markdown("---")
            st.subheader("📋 Données Brutes")
            # Expander = zone repliable pour ne pas surcharger l'interface
            with st.expander("Voir le tableau complet des stations"):
                st.dataframe(df, use_container_width=True)

        except Exception as e:
            st.error(f"Erreur données Tesla : {e}")
    else:
        # Message si aucune donnée n'est disponible
        st.info("👋 Bienvenue ! Aucune donnée trouvée. Lancez le scraping dans le menu de gauche.")

# ==========================================
# ONGLET 2 : DONNÉES MÉTÉOROLOGIQUES
# ==========================================

with tab_meteo:
    st.header("🌤️ Données Météorologiques (SYNOP)")
    
    # --- FILTRES ET SÉLECTION D'ANNÉE ---
    col_filter, col_btn = st.columns([1, 2])
    with col_filter:
        # Menu déroulant pour choisir l'année
        options_annee = ["Sélectionner"] + list(range(2022, 2010, -1))
        selected_year = st.selectbox("📅 Choisir une année de référence", options_annee, index=0)
    
    # Affichage d'info selon la sélection
    if selected_year != "Sélectionner":
        st.markdown(f"Données moyennes pour l'année **{selected_year}** (Server-Side Filter).")
    else:
        st.info("Veuillez choisir une année pour commencer.")

    # --- BOUTON D'ACTUALISATION DES DONNÉES ---
    with col_btn:
        st.write("")  # Espacement visuel
        if st.button("🔄 Actualiser Météo"):
            if selected_year == "Sélectionner":
                st.warning("⚠️ Veuillez sélectionner une année valide dans la liste avant d'actualiser.")
            else:
                # Affichage d'un spinner pendant le chargement
                with st.spinner(f'Récupération des données pour {selected_year}...'):
                    # Appel des fonctions API avec l'année choisie
                    df_meteo = get_meteo_data(year=selected_year, limit=1000)
                    df_poitiers = get_poitiers_data()
                    df_regions = get_region_comparison()
                    
                    # Stockage des données dans la session Streamlit
                    # Permet de garder les données en mémoire entre les interactions
                    st.session_state['df_meteo'] = df_meteo
                    st.session_state['df_poitiers'] = df_poitiers
                    st.session_state['df_regions'] = df_regions
                    st.session_state['selected_year'] = selected_year
                    
                    st.success(f"Données {selected_year} mises à jour avec succès !")
                    time.sleep(0.5)
                    st.rerun()  # Recharge la page pour afficher les nouvelles données

    # --- AFFICHAGE DES DONNÉES SI DISPONIBLES ---
    if 'df_meteo' in st.session_state and not st.session_state['df_meteo'].empty:
        df = st.session_state['df_meteo']
        display_year = st.session_state.get('selected_year', selected_year)
        
        # --- SECTION 1 : INDICATEURS CLÉS ---
        st.subheader(f"1. Indicateurs Clés ({display_year})")
        col1, col2, col3 = st.columns(3)
        
        # Calcul des métriques
        temp_moy = df['Temperature'].mean()
        ville_max = df.loc[df['Temperature'].idxmax()]['Ville'] if not df.empty else "N/A"
        temp_max_val = df['Temperature'].max()
        
        # Affichage des métriques
        col1.metric(f"Temp. Moyenne ({display_year})", f"{temp_moy:.1f} °C")
        col2.metric("Point le plus chaud", f"{ville_max}")
        col3.metric("Température max", f"{temp_max_val:.1f} °C")
        
        st.divider()

        # --- SECTION 2 : CARTE DES TEMPÉRATURES ---
        st.subheader("2. Carte des Températures")
        
        # Création de la carte centrée sur la France
        m = folium.Map(location=[46.603354, 1.888334], zoom_start=6)
        
        # Légende HTML fixée en bas à gauche
        legend_html = '''
             <div style="position: fixed; 
                         bottom: 50px; left: 50px; width: 150px; height: 100px; 
                         border:2px solid grey; z-index:9999; font-size:14px;
                         background-color:white; opacity:0.8;
                         padding: 10px;">
             <b>Températures</b><br>
             <i style="background:blue;width:10px;height:10px;display:inline-block;border-radius:50%"></i> < 10°C<br>
             <i style="background:orange;width:10px;height:10px;display:inline-block;border-radius:50%"></i> 10-25°C<br>
             <i style="background:red;width:10px;height:10px;display:inline-block;border-radius:50%"></i> > 25°C
             </div>
        '''
        m.get_root().html.add_child(folium.Element(legend_html))
        
        # Ajout d'un marqueur pour chaque station météo
        for index, row in df.iterrows():
            if 'lat' in row and 'lon' in row and pd.notnull(row['lat']) and pd.notnull(row['lon']):
                lat = row['lat']
                lon = row['lon']
                temp = row['Temperature']
                
                # Choix de la couleur selon la température
                color = 'blue'
                if temp > 10: color = 'orange'
                if temp > 25: color = 'red'
                
                # Ajout du marqueur
                folium.Marker(
                    location=[lat, lon],
                    popup=f"{row['Ville']}: {temp:.1f}°C",
                    tooltip=f"{row['Ville']}",
                    icon=folium.Icon(color=color, icon="cloud")
                ).add_to(m)
        
        # Affichage de la carte
        st_folium(m, use_container_width=True, height=600)
        
        st.divider()

        # --- SECTION 3 : COMPARAISON RÉGIONALE ---
        st.subheader("3. Comparaison Régionale (Multi-Années)")
        
        if 'df_regions' in st.session_state and not st.session_state['df_regions'].empty:
            df_reg = st.session_state['df_regions'].copy()
            
            # --- CONFIGURATION DU GRAPHIQUE ---
            with st.expander("⚙️ Configurer le graphique (Métriques & Années)", expanded=True):
                col_conf1, col_conf2 = st.columns(2)
                
                # Choix de la métrique à afficher
                with col_conf1:
                    metric_choice = st.radio(
                        "Choisir la métrique :",
                        ["Température Moyenne", "Pluie (rr24)"],
                        index=0,
                        horizontal=True
                    )
                    # Mapping du choix utilisateur vers le nom de colonne
                    col_map = {
                        "Température Moyenne": "Temperature",
                        "Pluie (rr24)": "Pluie"
                    }
                    y_axis = col_map[metric_choice]
                    y_label = "Température (°C)" if "Temp" in metric_choice else "Précipitations (mm)"
                
                # Sélection des années à afficher
                with col_conf2:
                    # Récupération des années disponibles dans les données
                    unique_years = sorted(df_reg['Annee'].dropna().unique().astype(int))
                    # Par défaut : 2018-2022 (exclusion de 2023 car données incomplètes)
                    default_years = [y for y in unique_years if 2018 <= y <= 2022]
                    
                    # Multi-sélection des années
                    selected_years_graph = st.multiselect(
                        "Filtrer les années :",
                        unique_years,
                        default=default_years
                    )

            # --- FILTRAGE DES DONNÉES ---
            # On ne garde que les années sélectionnées
            mask_years = df_reg['Annee'].astype(int).isin(selected_years_graph)
            df_graph = df_reg[mask_years].copy()
            
            if not df_graph.empty:
                # Conversion de l'année en chaîne pour Plotly (couleurs discrètes)
                df_graph['Annee_str'] = df_graph['Annee'].astype(int).astype(str)
                
                # Création du graphique en barres groupées
                fig = px.bar(
                    df_graph, 
                    x="Region",  # Axe X : régions
                    y=y_axis,  # Axe Y : métrique choisie
                    color="Annee_str",  # Couleur : année
                    barmode="group",  # Barres côte à côte
                    title=f"Comparaison : {metric_choice} par Région",
                    labels={
                        y_axis: y_label, 
                        "Region": "Région", 
                        "Annee_str": "Année"
                    },
                    height=500
                )
                
                # Rotation des étiquettes de l'axe X
                fig.update_layout(xaxis_tickangle=-45)
                st.plotly_chart(fig, use_container_width=True)
            else:
                st.warning("Aucune donnée pour les années sélectionnées.")

            # Zone pour voir les données brutes (debug)
            with st.expander("🔍 Voir les données brutes"):
                st.dataframe(df_graph)
        else:
            st.warning("Données régionales insuffisantes ou non chargées.")

        st.divider()

        # --- SECTION 4 : FOCUS ZONE POITIERS ---
        st.subheader("4. Focus Zone Poitiers (< 100km)")
        
        if 'df_poitiers' in st.session_state and not st.session_state['df_poitiers'].empty:
            df_p = st.session_state['df_poitiers']
            nb_stations = len(df_p)
            st.metric("Nombre de stations relevées (<100km de Poitiers)", nb_stations)
            # Affichage du tableau avec formatage des températures
            st.dataframe(df_p.style.format({"Temperature": "{:.1f} °C"}))
        else:
            st.info("Cliquez sur 'Actualiser' pour charger les données de Poitiers.")

    else:
        # Messages selon l'état de chargement des données
        if 'selected_year' in st.session_state and ('df_meteo' not in st.session_state or st.session_state['df_meteo'].empty):
             st.warning(f"Aucune donnée disponible pour l'année {st.session_state['selected_year']}. Essayez une autre année (ex: 2022, 2021).")
        else:
             st.info("Veuillez cliquer sur le bouton 'Actualiser Météo' pour charger les données.")
