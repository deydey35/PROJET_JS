import pandas as pd
import os
import plotly.express as px
import plotly.graph_objects as go
from dash import Dash, html, dcc, dash_table, Input, Output, State, callback
import dash_bootstrap_components as dbc

# Import des fonctions API depuis api_weather.py
from api_weather import get_meteo_data, get_poitiers_data, get_region_comparison


# ==========================================
# INITIALISATION DE L'APPLICATION DASH
# ==========================================

app = Dash(__name__, external_stylesheets=[dbc.themes.BOOTSTRAP])
app.title = "🌤️ Dashboard Météo"

# ==========================================
# FONCTIONS UTILITAIRES
# ==========================================

def make_metric_card(title, value):
    """Crée une carte Bootstrap affichant un indicateur clé."""
    return dbc.Card(
        dbc.CardBody([
            html.H6(title, className="card-subtitle mb-2 text-muted"),
            html.H4(value, className="card-title"),
        ]),
        className="text-center shadow-sm mb-3"
    )


def build_map_figure(df):
    """Construit une carte Plotly scatter_mapbox des températures."""
    if df.empty:
        return go.Figure()

    df = df.copy()
    # Filtrer les lignes avec coordonnées valides
    df = df.dropna(subset=['lat', 'lon', 'Temperature'])

    # Choix de la couleur selon la température
    def temp_color(t):
        if t > 25:
            return 'red'
        elif t > 10:
            return 'orange'
        return 'blue'

    df['color'] = df['Temperature'].apply(temp_color)
    df['text'] = df.apply(lambda r: f"{r['Ville']}: {r['Temperature']:.1f}°C", axis=1)

    fig = px.scatter_mapbox(
        df,
        lat='lat',
        lon='lon',
        hover_name='Ville',
        hover_data={'Temperature': ':.1f', 'lat': False, 'lon': False},
        color='color',
        color_discrete_map={'blue': 'blue', 'orange': 'orange', 'red': 'red'},
        text='text',
        zoom=5,
        height=600,
        title="Carte des Températures"
    )
    fig.update_layout(
        mapbox_style="open-street-map",
        mapbox_center={"lat": 46.603354, "lon": 1.888334},
        legend_title_text="Température",
        margin={"r": 0, "t": 40, "l": 0, "b": 0}
    )
    # Renommer les entrées de la légende
    fig.for_each_trace(lambda t: t.update(
        name={'blue': '< 10°C', 'orange': '10-25°C', 'red': '> 25°C'}.get(t.name, t.name)
    ))
    fig.update_traces(textposition='top center', textfont_size=9)
    return fig


def build_region_bar(df_reg, y_axis, metric_choice, y_label, selected_years):
    """Construit le graphique en barres de comparaison régionale."""
    if df_reg.empty:
        return go.Figure()

    mask = df_reg['Annee'].astype(int).isin(selected_years)
    df_graph = df_reg[mask].copy()

    if df_graph.empty:
        return go.Figure()

    df_graph['Annee_str'] = df_graph['Annee'].astype(int).astype(str)

    fig = px.bar(
        df_graph,
        x="Region",
        y=y_axis,
        color="Annee_str",
        barmode="group",
        title=f"Comparaison : {metric_choice} par Région",
        labels={y_axis: y_label, "Region": "Région", "Annee_str": "Année"},
        height=500
    )
    fig.update_layout(xaxis_tickangle=-45)
    return fig


# ==========================================
# OPTIONS ANNÉE
# ==========================================
options_annee = [{"label": str(y), "value": y} for y in range(2022, 2010, -1)]

# ==========================================
# LAYOUT
# ==========================================

app.layout = dbc.Container([

    # --- EN-TÊTE ---
    dbc.Row(dbc.Col(html.H2("🌤️ Données Météorologiques (SYNOP)"), className="my-3")),

    # --- FILTRES ET BOUTON ---
    dbc.Row([
        dbc.Col([
            html.Label("📅 Choisir une année de référence", className="fw-bold"),
            dcc.Dropdown(
                id='dropdown-annee',
                options=options_annee,
                value=None,
                placeholder="Sélectionner une année..."
            ),
        ], md=4),
        dbc.Col([
            html.Br(),
            dbc.Button("🔄 Actualiser Météo", id='btn-refresh', color='primary', className='mt-1'),
        ], md=4),
        dbc.Col([
            html.Div(id='status-message', className='mt-3')
        ], md=4),
    ], className="mb-4"),

    # --- Store caché pour conserver les données entre callbacks ---
    dcc.Store(id='store-meteo'),
    dcc.Store(id='store-poitiers'),
    dcc.Store(id='store-regions'),
    dcc.Store(id='store-year'),

    # --- SECTION 1 : INDICATEURS CLÉS ---
    html.Hr(),
    html.H4(id='titre-indicateurs'),
    dbc.Row(id='row-metrics', className="mb-4"),

    # --- SECTION 2 : CARTE ---
    html.Hr(),
    html.H4("2. Carte des Températures"),
    dcc.Graph(id='map-temperatures', figure=go.Figure()),

    # --- SECTION 3 : COMPARAISON RÉGIONALE ---
    html.Hr(),
    html.H4("3. Comparaison Régionale (Multi-Années)"),
    dbc.Row([
        dbc.Col([
            html.Label("Choisir la métrique :", className="fw-bold"),
            dcc.RadioItems(
                id='radio-metric',
                options=[
                    {"label": " Température Moyenne", "value": "Temperature"},
                    {"label": " Pluie (rr24)", "value": "Pluie"},
                ],
                value="Temperature",
                inline=True
            ),
        ], md=6),
        dbc.Col([
            html.Label("Filtrer les années :", className="fw-bold"),
            dcc.Dropdown(id='dropdown-years-graph', multi=True, placeholder="Sélectionner les années..."),
        ], md=6),
    ], className="mb-3"),
    dcc.Graph(id='bar-regions', figure=go.Figure()),

    # --- Données brutes (tableau) ---
    html.Details([
        html.Summary("🔍 Voir les données brutes"),
        dash_table.DataTable(
            id='table-raw-regions',
            style_table={'overflowX': 'auto'},
            style_cell={'textAlign': 'left', 'padding': '5px'},
            style_header={'fontWeight': 'bold', 'backgroundColor': '#f8f9fa'},
            page_size=15
        )
    ], className="mb-4"),

    # --- SECTION 4 : FOCUS POITIERS ---
    html.Hr(),
    html.H4("4. Focus Zone Poitiers (< 100km)"),
    html.Div(id='poitiers-metric'),
    dash_table.DataTable(
        id='table-poitiers',
        style_table={'overflowX': 'auto'},
        style_cell={'textAlign': 'left', 'padding': '5px'},
        style_header={'fontWeight': 'bold', 'backgroundColor': '#f8f9fa'},
        page_size=15
    ),

    # --- Message par défaut ---
    html.Div(id='placeholder-message', className='my-4'),

], fluid=True)


# ==========================================
# CALLBACKS
# ==========================================

@callback(
    Output('store-meteo', 'data'),
    Output('store-poitiers', 'data'),
    Output('store-regions', 'data'),
    Output('store-year', 'data'),
    Output('status-message', 'children'),
    Input('btn-refresh', 'n_clicks'),
    State('dropdown-annee', 'value'),
    prevent_initial_call=True
)
def fetch_data(n_clicks, selected_year):
    """Callback déclenché par le bouton Actualiser : récupère les données API."""
    if not selected_year:
        return None, None, None, None, dbc.Alert(
            "⚠️ Veuillez sélectionner une année valide.", color="warning"
        )

    df_meteo = get_meteo_data(year=selected_year, limit=1000)
    df_poitiers = get_poitiers_data()
    df_regions = get_region_comparison()

    if df_meteo.empty:
        return None, None, None, selected_year, dbc.Alert(
            f"Aucune donnée disponible pour {selected_year}. Essayez une autre année.",
            color="warning"
        )

    return (
        df_meteo.to_json(date_format='iso', orient='split'),
        df_poitiers.to_json(date_format='iso', orient='split') if not df_poitiers.empty else None,
        df_regions.to_json(date_format='iso', orient='split') if not df_regions.empty else None,
        selected_year,
        dbc.Alert(f"✅ Données {selected_year} mises à jour avec succès !", color="success", duration=4000)
    )


@callback(
    Output('titre-indicateurs', 'children'),
    Output('row-metrics', 'children'),
    Output('map-temperatures', 'figure'),
    Input('store-meteo', 'data'),
    State('store-year', 'data'),
)
def update_meteo_section(meteo_json, display_year):
    """Met à jour les indicateurs clés et la carte lorsque les données changent."""
    if not meteo_json:
        return "1. Indicateurs Clés", [], go.Figure()

    df = pd.read_json(meteo_json, orient='split')
    if df.empty:
        return "1. Indicateurs Clés", [], go.Figure()

    year_str = display_year or ""

    # Calcul des métriques
    temp_moy = df['Temperature'].mean()
    ville_max = df.loc[df['Temperature'].idxmax()]['Ville'] if not df.empty else "N/A"
    temp_max_val = df['Temperature'].max()

    metrics = [
        dbc.Col(make_metric_card(f"Temp. Moyenne ({year_str})", f"{temp_moy:.1f} °C"), md=4),
        dbc.Col(make_metric_card("Point le plus chaud", str(ville_max)), md=4),
        dbc.Col(make_metric_card("Température max", f"{temp_max_val:.1f} °C"), md=4),
    ]

    fig_map = build_map_figure(df)

    return f"1. Indicateurs Clés ({year_str})", metrics, fig_map


@callback(
    Output('dropdown-years-graph', 'options'),
    Output('dropdown-years-graph', 'value'),
    Input('store-regions', 'data'),
)
def update_year_dropdown(regions_json):
    """Remplit le dropdown des années disponibles pour la comparaison régionale."""
    if not regions_json:
        return [], []

    df_reg = pd.read_json(regions_json, orient='split')
    if df_reg.empty or 'Annee' not in df_reg.columns:
        return [], []

    unique_years = sorted(df_reg['Annee'].dropna().unique().astype(int))
    options = [{"label": str(y), "value": y} for y in unique_years]
    default = [y for y in unique_years if 2018 <= y <= 2022]

    return options, default


@callback(
    Output('bar-regions', 'figure'),
    Output('table-raw-regions', 'data'),
    Output('table-raw-regions', 'columns'),
    Input('radio-metric', 'value'),
    Input('dropdown-years-graph', 'value'),
    State('store-regions', 'data'),
)
def update_region_chart(y_axis, selected_years, regions_json):
    """Met à jour le graphique de comparaison régionale."""
    if not regions_json or not selected_years:
        return go.Figure(), [], []

    df_reg = pd.read_json(regions_json, orient='split')
    if df_reg.empty:
        return go.Figure(), [], []

    # Mapping de la métrique
    metric_label = "Température Moyenne" if y_axis == "Temperature" else "Pluie (rr24)"
    y_label = "Température (°C)" if y_axis == "Temperature" else "Précipitations (mm)"

    fig = build_region_bar(df_reg, y_axis, metric_label, y_label, selected_years)

    # Données brutes filtrées pour le tableau
    mask = df_reg['Annee'].astype(int).isin(selected_years)
    df_table = df_reg[mask].copy()
    columns = [{"name": c, "id": c} for c in df_table.columns]

    return fig, df_table.to_dict('records'), columns


@callback(
    Output('poitiers-metric', 'children'),
    Output('table-poitiers', 'data'),
    Output('table-poitiers', 'columns'),
    Input('store-poitiers', 'data'),
)
def update_poitiers(poitiers_json):
    """Met à jour la section Focus Poitiers."""
    if not poitiers_json:
        return dbc.Alert("Cliquez sur 'Actualiser Météo' pour charger les données de Poitiers.", color="info"), [], []

    df_p = pd.read_json(poitiers_json, orient='split')
    if df_p.empty:
        return dbc.Alert("Aucune donnée Poitiers disponible.", color="warning"), [], []

    nb_stations = len(df_p)

    # Formater la température
    if 'Temperature' in df_p.columns:
        df_p['Temperature'] = df_p['Temperature'].apply(lambda x: f"{x:.1f} °C" if pd.notnull(x) else "")

    # Colonnes pertinentes pour l'affichage
    display_cols = [c for c in ['Ville', 'Date', 'Temperature', 'Pluie_24h'] if c in df_p.columns]
    df_display = df_p[display_cols] if display_cols else df_p

    columns = [{"name": c, "id": c} for c in df_display.columns]

    metric_div = html.Div([
        dbc.Badge(f"Nombre de stations relevées (<100km de Poitiers) : {nb_stations}",
                  color="primary", className="fs-6 mb-2")
    ])

    return metric_div, df_display.to_dict('records'), columns


# ==========================================
# LANCEMENT DU SERVEUR
# ==========================================

if __name__ == '__main__':
    app.run(debug=True, port=8050)
