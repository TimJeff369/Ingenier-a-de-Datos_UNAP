import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from scipy.stats import poisson
import numpy as np
import json 

# --- 1. CONFIGURACIÓN DE LA PÁGINA ---
st.set_page_config(page_title="Dashboard Predictivo Puno/Juliaca", layout="wide")

st.title("📊 Sistema de Inteligencia Territorial Criminal")
st.markdown("Análisis avanzado de patrones delictivos y vulnerabilidad socioeconómica.")

# --- 2. INGENIERÍA DE DATOS (INGESTA Y AGREGACIÓN REGIONAL) ---
@st.cache_data
def cargar_datos_procesados():
    try:
        # A. Carga de Archivos Principales
        df_crimen = pd.read_csv("datos.csv", encoding='latin-1', on_bad_lines='skip', sep=None, engine='python')
        df_socio = pd.read_csv("ubigeo_distrito.csv", encoding='latin-1', on_bad_lines='skip', sep=None, engine='python')
        
        with open("peru_departamentos.geojson", encoding='utf-8') as f:
            geojson_peru = json.load(f)

        # Limpiamos nombres de columnas (quita espacios en blanco accidentales)
        df_crimen.columns = df_crimen.columns.str.strip()
        df_socio.columns = df_socio.columns.str.strip()

        # Renombramos el UBIGEO sea cual sea su nombre exacto
        if 'UBIGEO_HECHO' in df_crimen.columns:
            df_crimen.rename(columns={'UBIGEO_HECHO': 'inei'}, inplace=True)
        elif 'UBIGEO' in df_crimen.columns:
            df_crimen.rename(columns={'UBIGEO': 'inei'}, inplace=True)
            
        df_crimen.fillna(0, inplace=True)

        # B. Ingeniería 1: Preparación de Datos de Crimen (Melt/Transformación)
        # Si el archivo NO tiene la columna 'Año', asumimos que los años están en columnas (2017, 2018...)
        if 'Año' not in df_crimen.columns:
            columnas_fijas = [col for col in df_crimen.columns if not col.isdigit()]
            columnas_anios = [col for col in df_crimen.columns if col.isdigit()]
            
            if len(columnas_anios) > 0:
                # Transformamos las columnas de años en filas
                df_crimen = pd.melt(df_crimen, id_vars=columnas_fijas, value_vars=columnas_anios, 
                                    var_name='Año', value_name='Denuncias')
            else:
                # Caso de rescate si el CSV tiene otro formato
                df_crimen['Año'] = '2019'
                if 'Denuncias' not in df_crimen.columns:
                    df_crimen['Denuncias'] = 1

        # C. Ingeniería 2: Cruce de Datos (Merge)
        # Forzamos a texto para que no haya errores
        df_crimen['inei'] = df_crimen['inei'].astype(str)
        df_socio['inei'] = df_socio['inei'].astype(str)
        
        df_distrital = pd.merge(df_crimen, 
                                df_socio[['inei', 'region', 'superficie', 'pob_densidad_2020', 
                                          'altitude', 'pct_pobreza_total', 'pct_pobreza_extrema']], 
                                on='inei', how='left')
        
        # Limpiamos nulos después del cruce
        df_distrital['Denuncias'] = pd.to_numeric(df_distrital['Denuncias'], errors='coerce').fillna(0)
        df_distrital.fillna(0, inplace=True)

        # D. Ingeniería 3: Agregación a Nivel Regional (Departamento)
        df_regional = df_distrital.groupby(['DPTO_HECHO', 'Año']).agg({
            'Denuncias': 'sum',
            'superficie': 'sum',
            'pob_densidad_2020': 'mean',
            'altitude': 'mean',
            'pct_pobreza_total': 'mean',
            'pct_pobreza_extrema': 'mean'
        }).reset_index()

        df_regional_mapa = df_regional.groupby('DPTO_HECHO').agg({
            'Denuncias': 'sum',
            'superficie': 'first',
            'pob_densidad_2020': 'first',
            'altitude': 'first',
            'pct_pobreza_total': 'first',
            'pct_pobreza_extrema': 'first'
        }).reset_index()

        return df_distrital, df_regional, df_regional_mapa, geojson_peru
        
    except Exception as e:
        st.error(f"🚨 Error fatal en la ingeniería de datos: {e}")
        st.stop()

# Cargamos los DataFrames procesados
df_distrital, df_regional, df_regional_mapa, geojson_peru = cargar_datos_procesados()

# --- 3. BARRA LATERAL (FILTROS EN CASCADA) ---
st.sidebar.header("Filtros de Análisis Local")

if not df_distrital.empty and 'DPTO_HECHO' in df_distrital.columns:
    regiones = sorted(df_distrital['DPTO_HECHO'].unique().tolist())
    region_sel = st.sidebar.selectbox("1. Selecciona una Región:", regiones, index=regiones.index('PUNO') if 'PUNO' in regiones else 0)

    provincias = sorted(df_distrital[df_distrital['DPTO_HECHO'] == region_sel]['PROV_HECHO'].unique().tolist())
    provincia_sel = st.sidebar.selectbox("2. Selecciona una Provincia:", provincias)

    distritos = sorted(df_distrital[(df_distrital['DPTO_HECHO'] == region_sel) & (df_distrital['PROV_HECHO'] == provincia_sel)]['DIST_HECHO'].unique().tolist())
    distrito_sel = st.sidebar.selectbox("3. Selecciona un Distrito:", distritos)
else:
    st.sidebar.warning("⚠️ No se detectaron departamentos. Verifica las columnas de tu CSV.")
    region_sel = provincia_sel = distrito_sel = None

# =========================================================================
# --- 4. SECCIÓN 1: MAPA REGIONAL COMPLETO Y DINÁMICO ---
# =========================================================================
st.header("🗺️ Panorama Nacional de Criminalidad y Vulnerabilidad")
st.write("Mapa interactivo que correlaciona el total de denuncias con indicadores socioeconómicos clave.")

if not df_regional_mapa.empty:
    fig_choropleth = px.choropleth(df_regional_mapa, 
                                   geojson=geojson_peru, 
                                   locations='DPTO_HECHO', 
                                   featureidkey='properties.NOMBDEP', 
                                   color='Denuncias', 
                                   color_continuous_scale="Reds", 
                                   range_color=(0, df_regional_mapa['Denuncias'].max() * 0.8), 
                                   mapbox_style="carto-positron", 
                                   zoom=4.2, 
                                   center={"lat": -9.189967, "lon": -75.015152}, 
                                   opacity=0.7,
                                   labels={'Denuncias': 'Total Denuncias'},
                                   title="Coropleta: Intensidad Delictiva por Departamento")

    fig_choropleth.update_traces(
        hovertemplate="<br>".join([
            "<b>Región: %{location}</b>",
            "Total Denuncias: %{color:,.0f}",
            "Pobreza Total: %{customdata[0]:.2f} %",
            "Pobreza Extrema: %{customdata[1]:.2f} %",
            "Densidad Poblacional: %{customdata[2]:,.2f} hab/km²",
            "Superficie: %{customdata[3]:,.2f} km²"
        ]),
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
    df_prov_clave = df_distrital[df_distrital['PROV_HECHO'].isin(['PUNO', 'SAN ROMAN', 'AZANGARO'])]
    if not df_prov_clave.empty:
        df_prov_evol = df_prov_clave.groupby(['PROV_HECHO', 'Año'])['Denuncias'].sum().reset_index()
        fig_prov = px.line(df_prov_evol, x='Año', y='Denuncias', color='PROV_HECHO', markers=True,
                           title="Tendencia en Provincias Principales",
                           labels={'PROV_HECHO': 'Provincia'})
        st.plotly_chart(fig_prov, use_container_width=True)
    else:
        st.info("No se encontraron datos históricos para Puno, San Román o Azángaro.")

with col_der:
    st.write(f"### Histórico Distrital: {distrito_sel}")
    if distrito_sel:
        df_dist_sel = df_distrital[(df_distrital['DPTO_HECHO'] == region_sel) & 
                                   (df_distrital['PROV_HECHO'] == provincia_sel) & 
                                   (df_distrital['DIST_HECHO'] == distrito_sel)]
        
        if not df_dist_sel.empty:
            fig_dist = px.bar(df_dist_sel, x='Año', y='Denuncias', color='Año', text='Denuncias',
                              title=f"Denuncias Registradas en {distrito_sel}")
            st.plotly_chart(fig_dist, use_container_width=True)

# =========================================================================
# --- 6. SECCIÓN 3: MODELO MATEMÁTICO (POISSON) ---
# =========================================================================
st.header("🧮 Modelo Predictivo (Distribución de Poisson)")

if distrito_sel and not df_dist_sel.empty:
    lambda_param = df_dist_sel['Denuncias'].mean()
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
        st.warning(f"La tasa histórica para {distrito_sel} es 0, no se puede calcular Poisson.")
else:
    st.warning("No hay suficientes datos para calcular el modelo predictor.")

st.markdown("---")
st.caption("Desarrollado para la monografía de Ingeniería - Universidad Nacional del Altiplano.")

