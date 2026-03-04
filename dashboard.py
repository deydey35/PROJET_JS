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
