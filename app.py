import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from scipy.stats import poisson
import numpy as np

# --- 1. CONFIGURACIÓN DE LA PÁGINA ---
st.set_page_config(page_title="Dashboard Predictivo Puno/Juliaca", layout="wide")

st.title("📊 Análisis y Predicción de Patrones Delictivos")
st.markdown("Comparativa de incidentes y cálculo probabilístico en la Región Puno.")

# --- 2. CARGA Y LIMPIEZA DE DATOS ---
@st.cache_data
def cargar_datos():
    # Asegúrate de que tu archivo se llame datos.xlsx y esté en la misma carpeta
    df = pd.read_excel("datos.xlsx")
    # Llenamos valores vacíos con 0 para evitar errores matemáticos
    df.fillna(0, inplace=True)
    return df

try:
    df = cargar_datos()
except FileNotFoundError:
    st.error("🚨 Archivo no encontrado. Sube tu archivo Excel como 'datos.xlsx' a tu Codespace.")
    st.stop()

# Transformar los datos: de columnas por año a filas (facilita las gráficas)
df_melt = pd.melt(df, id_vars=['DPTO_HECHO', 'PROV_HECHO', 'DIST_HECHO'], 
                  value_vars=['Denuncias_2017', 'Denuncias_2018', 'Denuncias_2019'],
                  var_name='Año', value_name='Denuncias')
# Limpiamos el texto para que solo diga el año (ej: "2017" en lugar de "Denuncias_2017")
df_melt['Año'] = df_melt['Año'].str.replace('Denuncias_', '')

# --- 3. BARRA LATERAL (FILTROS INTERACTIVOS) ---
st.sidebar.header("Filtros de Análisis")

# 1. Filtro de Región (Departamento)
regiones = sorted(df['DPTO_HECHO'].unique().tolist())
region_sel = st.sidebar.selectbox("1. Selecciona una Región (Departamento):", regiones)

# 2. Filtro de Provincia (Depende de la Región seleccionada)
provincias = sorted(df[df['DPTO_HECHO'] == region_sel]['PROV_HECHO'].unique().tolist())
provincia_sel = st.sidebar.selectbox("2. Selecciona una Provincia:", provincias)

# 3. Filtro de Distrito (Depende de la Provincia seleccionada)
distritos = sorted(df[(df['DPTO_HECHO'] == region_sel) & (df['PROV_HECHO'] == provincia_sel)]['DIST_HECHO'].unique().tolist())
distrito_sel = st.sidebar.selectbox("3. Selecciona un Distrito:", distritos)
# --- 4. SECCIÓN VISUAL: COMPARATIVA REGIONAL ---
st.header("📈 Comparativa Regional Destacada")
st.write("Evolución de las denuncias en las provincias clave de la región.")

# Agrupamos los datos por provincia y año
df_prov = df_melt.groupby(['PROV_HECHO', 'Año'])['Denuncias'].sum().reset_index()

# Filtramos para comparar específicamente Puno, San Román (Juliaca) y Azángaro
provincias_clave = ['PUNO', 'SAN ROMAN', 'AZANGARO']
df_prov_clave = df_prov[df_prov['PROV_HECHO'].isin(provincias_clave)]

# Gráfico de líneas comparativo
fig_prov = px.line(df_prov_clave, x='Año', y='Denuncias', color='PROV_HECHO', markers=True,
                   title="Evolución (2017-2019): Puno vs San Román (Juliaca) vs Azángaro",
                   labels={'PROV_HECHO': 'Provincia'})
st.plotly_chart(fig_prov, use_container_width=True)

# --- 5. SECCIÓN VISUAL: ANÁLISIS DISTRITAL ---
st.header(f"📍 Análisis Específico: {distrito_sel}")
# Filtramos los datos solo para el distrito seleccionado en la barra lateral
df_dist = df_melt[(df_melt['PROV_HECHO'] == provincia_sel) & (df_melt['DIST_HECHO'] == distrito_sel)]

# Gráfico de barras para el distrito
fig_dist = px.bar(df_dist, x='Año', y='Denuncias', color='Año', text='Denuncias',
                  title=f"Denuncias Registradas (2017-2019) en {distrito_sel}")
st.plotly_chart(fig_dist, use_container_width=True)

# --- 6. SECCIÓN MATEMÁTICA: MODELO DE POISSON ---
st.header("🧮 Modelo Predictivo (Distribución de Poisson)")
st.write("Cálculo de la probabilidad de ocurrencia para el próximo periodo basado en la tasa histórica.")

# Calculamos Lambda (El promedio histórico del distrito seleccionado)
lambda_param = df_dist['Denuncias'].mean()
st.info(f"**Tasa media histórica (λ) para {distrito_sel}:** {lambda_param:.2f} denuncias anuales.")

col1, col2 = st.columns(2)

with col1:
    # El usuario elige cuántos eventos quiere predecir (k)
    st.write("### Simulador de Probabilidad")
    k_val = st.number_input("¿Qué cantidad de denuncias deseas predecir? (k):", 
                            min_value=0, value=int(lambda_param), step=1)
    
    # Aplicación matemática de la función de Poisson
    probabilidad = poisson.pmf(k_val, lambda_param) * 100 # Convertimos a porcentaje
    st.metric(label=f"Probabilidad de registrar exactamente {k_val} denuncias:", value=f"{probabilidad:.2f} %")

with col2:
    # Gráfico de la campana de probabilidades de Poisson
    x_vals = np.arange(0, int(lambda_param * 2.5) + 5)
    y_vals = poisson.pmf(x_vals, lambda_param)
    
    fig_poisson = go.Figure(data=[go.Bar(x=x_vals, y=y_vals, marker_color='indigo')])
    fig_poisson.update_layout(title="Curva de Distribución de Probabilidades",
                              xaxis_title="Número de Denuncias (k)",
                              yaxis_title="Probabilidad")
    # Línea vertical marcando la media
    fig_poisson.add_vline(x=lambda_param, line_dash="dash", line_color="red", annotation_text="Media Histórica")
    st.plotly_chart(fig_poisson, use_container_width=True)

st.markdown("---")
st.caption("© 2026 Todos los Derechos Reservados - Universidad Nacional del Altiplano.")
st.caption("© 2026 Todos los Derechos Reservados - Universidad Nacional del Altiplano.")