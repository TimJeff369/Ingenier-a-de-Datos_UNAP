import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from scipy.stats import poisson
import numpy as np
import json # Necesario para leer el archivo GeoJSON

# --- 1. CONFIGURACIÓN DE LA PÁGINA ---
st.set_page_config(page_title="Dashboard Predictivo Puno/Juliaca", layout="wide")

st.title("📊 Sistema de Inteligencia Territorial Criminal")
st.markdown("Análisis avanzado de patrones delictivos y vulnerabilidad socioeconómica.")

# --- 2. INGENIERÍA DE DATOS (INGESTA Y AGREGACIÓN REGIONAL) ---
@st.cache_data
def cargar_datos_procesados():
    # A. Carga de Archivos Principales
    try:
# El parámetro 'on_bad_lines' saltará las filas que tengan errores
        # 'sep' le dice que use la coma como separador (o usa ';' si tu Excel original era en español)
        df_crimen = pd.read_csv("datos.csv", on_bad_lines='skip', sep=None, engine='python')
        
        df_crimen.fillna(0, inplace=True)
        df_crimen.rename(columns={'UBIGEO_HECHO': 'inei'}, inplace=True)

        # Para el de los ubigeos, si sigue dando guerra, hazle lo mismo:
        df_socio = pd.read_csv("ubigeo_distrito.csv", on_bad_lines='skip', sep=None, engine='python')
        
        # Archivo GeoJSON: Polígonos de departamentos
        with open("peru_departamentos.geojson", encoding='utf-8') as f:
            geojson_peru = json.load(f)
            
    except FileNotFoundError as e:
        st.error(f"🚨 Error al cargar archivos. Asegúrate de tener 'datos.xlsx', 'ubigeo_distrito.xlsx' y 'peru_departamentos.geojson' en tu Codespace. Error: {e}")
        st.stop()

    # ---------------------------------------------------------
    # B. Ingeniería 1: Preparación de Datos de Crimen (Melt)
    # ---------------------------------------------------------
    df_crimen_melt = pd.melt(df_crimen, id_vars=['DPTO_HECHO', 'PROV_HECHO', 'DIST_HECHO', 'inei'], 
                            value_vars=['Denuncias_2017', 'Denuncias_2018', 'Denuncias_2019'],
                            var_name='Año', value_name='Denuncias')
    df_crimen_melt['Año'] = df_crimen_melt['Año'].str.replace('Denuncias_', '')

    # ---------------------------------------------------------
    # C. Ingeniería 2: Cruce de Datos a Nivel Distrital
    # ---------------------------------------------------------
    # Unimos crimen con datos socioeconómicos usando 'inei' como llave
    df_distrital = pd.merge(df_crimen_melt, 
                            df_socio[['inei', 'region', 'superficie', 'pob_densidad_2020', 
                                      'altitude', 'pct_pobreza_total', 'pct_pobreza_extrema']], 
                            on='inei', how='left')

    # ---------------------------------------------------------
    # D. Ingeniería 3: AGREGACIÓN A NIVEL REGIONAL (Departamento)
    # ---------------------------------------------------------
    # Agrupamos por Departamento y Año
    df_regional = df_distrital.groupby(['DPTO_HECHO', 'Año']).agg({
        'Denuncias': 'sum', # Sumamos las denuncias de todos sus distritos
        'superficie': 'sum', # Sumamos la superficie total
        'pob_densidad_2020': 'mean', # Promediamos la densidad
        'altitude': 'mean', # Promediamos la altitud
        'pct_pobreza_total': 'mean', # Promediamos la pobreza
        'pct_pobreza_extrema': 'mean' # Promediamos la pobreza extrema
    }).reset_index()

    # Creamos un DataFrame regional consolidado (sin Año) para el mapa general
    # Calculamos el total de denuncias 2017-2019
    df_regional_mapa = df_regional.groupby('DPTO_HECHO').agg({
        'Denuncias': 'sum',
        'superficie': 'first', # Datos socioeconómicos son fijos
        'pob_densidad_2020': 'first',
        'altitude': 'first',
        'pct_pobreza_total': 'first',
        'pct_pobreza_extrema': 'first'
    }).reset_index()

    return df_distrital, df_regional, df_regional_mapa, geojson_peru

# Cargamos los DataFrames procesados
df_distrital, df_regional, df_regional_mapa, geojson_peru = cargar_datos_procesados()

# --- 3. BARRA LATERAL (FILTROS EN CASCADA) ---
st.sidebar.header("Filtros de Análisis Local")

# Filtro 1: Región (De tus nuevos datos)
regiones = sorted(df_distrital['DPTO_HECHO'].unique().tolist())
region_sel = st.sidebar.selectbox("1. Selecciona una Región:", regiones, index=regiones.index('PUNO') if 'PUNO' in regiones else 0)

# Filtro 2: Provincia (Depende de Región)
provincias = sorted(df_distrital[df_distrital['DPTO_HECHO'] == region_sel]['PROV_HECHO'].unique().tolist())
provincia_sel = st.sidebar.selectbox("2. Selecciona una Provincia:", provincias)

# Filtro 3: Distrito (Depende de Provincia)
distritos = sorted(df_distrital[(df_distrital['DPTO_HECHO'] == region_sel) & (df_distrital['PROV_HECHO'] == provincia_sel)]['DIST_HECHO'].unique().tolist())
distrito_sel = st.sidebar.selectbox("3. Selecciona un Distrito:", distritos)


# =========================================================================
# --- 4. SECCIÓN 1: MAPA REGIONAL COMPLETO Y DINÁMICO ---
# =========================================================================
st.header("🗺️ Panorama Nacional de Criminalidad y Vulnerabilidad")
st.write("Mapa interactivo que correlaciona el total de denuncias (2017-2019) con indicadores socioeconómicos clave.")

# Usamos ChoroplethMap para colorear los departamentos según denuncias
fig_choropleth = px.choropleth(df_regional_mapa, 
                               geojson=geojson_peru, 
                               locations='DPTO_HECHO', # Columna en DF
                               featureidkey='properties.NOMBDEP', # Llave dentro del GeoJSON
                               color='Denuncias', # Variable que define el color
                               color_continuous_scale="Reds", # Escala de calor para crímenes
                               range_color=(0, df_regional_mapa['Denuncias'].max() * 0.8), # Ajuste de contraste
                               mapbox_style="carto-positron", # Mapa base limpio
                               zoom=4.2, 
                               center={"lat": -9.189967, "lon": -75.015152}, # Centro del Perú
                               opacity=0.7,
                               labels={'Denuncias': 'Total Denuncias (17-19)'},
                               title="Coropleta: Intensidad Delictiva por Departamento")

# ¡LA MAGIA DEL HOVER! Definimos qué sale al pasar el mouse
fig_choropleth.update_traces(
    hovertemplate="<br>".join([
        "<b>Región: %{location}</b>",
        "Total Denuncias: %{color:,.0f}",
        "Pobreza Total: %{customdata[0]:.2f} %",
        "Pobreza Extrema: %{customdata[1]:.2f} %",
        "Densidad Poblacional: %{customdata[2]:,.2f} hab/km²",
        "Superficie: %{customdata[3]:,.2f} km²"
    ]),
    # Definimos los datos socioeconómicos de tu Excel 2 para el hover
    customdata=df_regional_mapa[['pct_pobreza_total', 'pct_pobreza_extrema', 
                                 'pob_densidad_2020', 'superficie']]
)

fig_choropleth.update_layout(margin={"r":0,"t":40,"l":0,"b":0})
st.plotly_chart(fig_choropleth, use_container_width=True)


# =========================================================================
# --- 5. SECCIÓN 2: COMPARATIVA REGIONAL Y LOCAL ---
# =========================================================================
st.header(f"📈 Análisis Comparativo Regional y Local")

col_izq, col_der = st.columns(2)

with col_izq:
    st.write("### Evolución en Provincias Clave (Puno/Juliaca/Azángaro)")
    # Agrupamos por provincia para la gráfica
    df_prov_clave = df_distrital[df_distrital['PROV_HECHO'].isin(['PUNO', 'SAN ROMAN', 'AZANGARO'])]
    df_prov_evol = df_prov_clave.groupby(['PROV_HECHO', 'Año'])['Denuncias'].sum().reset_index()

    fig_prov = px.line(df_prov_evol, x='Año', y='Denuncias', color='PROV_HECHO', markers=True,
                       title="Tendencia en Provincias Principales",
                       labels={'PROV_HECHO': 'Provincia'})
    st.plotly_chart(fig_prov, use_container_width=True)

with col_der:
    st.write(f"### Histórico Distrital: {distrito_sel}")
    # Usamos los datos distritales filtrados por la barra lateral
    df_dist_sel = df_distrital[(df_distrital['DPTO_HECHO'] == region_sel) & 
                                (df_distrital['PROV_HECHO'] == provincia_sel) & 
                                (df_distrital['DIST_HECHO'] == distrito_sel)]
    
    fig_dist = px.bar(df_dist_sel, x='Año', y='Denuncias', color='Año', text='Denuncias',
                      title=f"Denuncias Registradas en {distrito_sel}")
    st.plotly_chart(fig_dist, use_container_width=True)


# =========================================================================
# --- 6. SECCIÓN 3: MODELO MATEMÁTICO (POISSON) ---
# =========================================================================
# (Esta sección se mantiene igual, usando df_dist_sel)
st.header("🧮 Modelo Predictivo (Distribución de Poisson)")
# ... (mismo código de Poisson que ya tenías)
# Calculamos Lambda
lambda_param = df_dist_sel['Denuncias'].mean() if not df_dist_sel.empty else 0
if lambda_param > 0:
    st.info(f"**Tasa media histórica (λ) para {distrito_sel}:** {lambda_param:.2f} denuncias anuales.")
    col1, col2 = st.columns(2)
    with col1:
        st.write("### Simulador de Probabilidad")
        k_val = st.number_input("¿Qué cantidad de denuncias deseas predecir? (k):", min_value=0, value=int(lambda_param), step=1)
        probabilidad = poisson.pmf(k_val, lambda_param) * 100 
        st.metric(label=f"Probabilidad de registrar exactamente {k_val} denuncias:", value=f"{probabilidad:.2f} %")
    with col2:
        x_vals = np.arange(0, int(lambda_param * 2.5) + 5)
        y_vals = poisson.pmf(x_vals, lambda_param)
        fig_poisson = go.Figure(data=[go.Bar(x=x_vals, y=y_vals, marker_color='indigo')])
        fig_poisson.update_layout(title="Curva de Distribución de Probabilidades", xaxis_title="Número de Denuncias (k)", yaxis_title="Probabilidad")
        st.plotly_chart(fig_poisson, use_container_width=True)
else:
    st.warning(f"No hay suficientes datos históricos para {distrito_sel} para calcular el modelo predictor.")

st.markdown("---")
st.caption("Desarrollado para la monografía de Ingeniería - Universidad Nacional del Altiplano.")