import streamlit as st
from scipy.stats import poisson
import pandas as pd
import plotly.express as px
import numpy as np


import streamlit as st

# --- INYECTAR FUENTE OSWALD ---
st.markdown(
    """
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Oswald:wght@200..700&display=swap');

    html, body, [class*="css"], .stMarkdown, h1, h2, h3, h4, h5, h6, p, div {
        font-family: 'Oswald', sans-serif !important;
    }
    </style>
    """,
    unsafe_allow_html=True
)




st.set_page_config(page_title="Seguridad Puno", layout="wide")

st.title("🛡️ Sistema Predictivo de Inseguridad - Región Puno")

# Sidebar
st.sidebar.header("Configuración de Zona")
ciudad = st.sidebar.selectbox("Selecciona la ciudad:", ["Puno", "Juliaca", "Azángaro"])

# Datos simulados (promedios diarios)
promedios = {"Puno": 1.5, "Juliaca": 3.8, "Azángaro": 0.8}
lambda_actual = promedios[ciudad]

col1, col2 = st.columns(2)

with col1:
    st.subheader(f"Análisis de Riesgo en {ciudad}")
    st.write(f"El promedio diario ($\lambda$) es: **{lambda_actual}**")
    
    eventos = st.slider("Número de incidentes a predecir:", 0, 10, 2)
    prob = poisson.pmf(eventos, lambda_actual) * 100
    
    st.metric(label=f"Probabilidad de que ocurran {eventos} incidentes", value=f"{prob:.2f}%")
    st.info("Este cálculo se basa en la función de masa de probabilidad (PMF) de Poisson.")

with col2:
    st.subheader("Distribución de Probabilidades")
    
    # Generar datos para el gráfico
    x = np.arange(0, 11)
    y = poisson.pmf(x, lambda_actual)
    df_grafico = pd.DataFrame({'Incidentes': x, 'Probabilidad': y})
    
    # Crear gráfico interactivo
    fig = px.bar(df_grafico, x='Incidentes', y='Probabilidad', 
                 title=f"Curva de Poisson para {ciudad}",
                 labels={'Probabilidad': 'Probabilidad (0-1)'},
                 color_continuous_scale='Reds')
    
    st.plotly_chart(fig, use_container_width=True)

st.success(f"Modelo calibrado para {ciudad} exitosamente.")























# --- SECCIÓN DEL MAPA DE RIESGO ---
st.subheader("📍 Mapa de Riesgo Geoespacial - Región Puno")

# Datos de coordenadas para el mapa (Simulados según tu lista de ciudades)
# Puedes ajustar los valores de 'Riesgo' para cambiar los colores
data_mapa = pd.DataFrame({
    'Ciudad': ['Puno', 'Juliaca', 'Azángaro'],
    'lat': [-15.8402, -15.4967, -14.9089],
    'lon': [-70.0219, -70.1333, -70.1889],
    'Riesgo': [1.5, 3.8, 0.8], # Usamos los lambdas (promedios)
    'Nivel': ['Medio', 'Alto', 'Bajo']
})

# Definir colores: Rojo (Alto), Naranja (Medio), Verde (Bajo)
def asignar_color(valor):
    if valor > 2.5: return 'red'
    elif valor > 1.0: return 'orange'
    else: return 'green'

data_mapa['Color'] = data_mapa['Riesgo'].apply(asignar_color)

import plotly.express as px

fig_mapa = px.scatter_mapbox(
    data_mapa, 
    lat="lat", 
    lon="lon", 
    color="Nivel",
    color_discrete_map={"Alto": "red", "Medio": "orange", "Bajo": "green"},
    size="Riesgo",
    hover_name="Ciudad",
    zoom=7, 
    height=500,
    mapbox_style="carto-positron"
)

st.plotly_chart(fig_mapa, use_container_width=True)














# --- PIE DE PÁGINA (FOOTER) ---
st.markdown("---") # Una línea divisoria para separar el contenido
st.markdown(
    """
    <div style="text-align: center;">
        <p>© 2026 Derechos Reservados - Universidad Nacional del Altiplano</p>
        <small>Investigación Estadística sobre Seguridad Ciudadana - Región Puno</small>
    </div>
    """,
    unsafe_allow_html=True
)

























import pandas as pd
from scipy.stats import poisson

# 1. Carga de datos con las columnas exactas de tu imagen
# He agregado 'prov_pjfs' para asegurar el filtrado si el ubigeo falla
df = pd.read_csv('delitos_denunciados_2019.csv', usecols=['ubigeo_pjfs', 'cantidad', 'fecha_corte', 'prov_pjfs'])

# --- TRUCO DE INGENIERÍA: Limpieza de datos ---
# Convertimos a string y quitamos espacios por si acaso
df['ubigeo_pjfs'] = df['ubigeo_pjfs'].astype(str).str.strip()
df['prov_pjfs'] = df['prov_pjfs'].astype(str).str.upper().str.strip()

# 2. Filtrado estratégico mejorado
# Filtramos por UBIGEO (como texto) O por nombre de PROVINCIA
data_juliaca = df[(df['ubigeo_pjfs'] == '211101') | (df['prov_pjfs'] == 'SAN ROMAN')]
data_puno = df[(df['ubigeo_pjfs'] == '210101') | (df['prov_pjfs'] == 'PUNO')]

# Comprobación de seguridad (Esto aparecerá en tu terminal)
print(f"Filas encontradas para Juliaca: {len(data_juliaca)}")
print(f"Filas encontradas para Puno: {len(data_puno)}")

# 3. Cálculo de la Tasa de Ocurrencia (Lambda)
dias = 365
# Usamos sum() por si la columna 'cantidad' tiene valores mayores a 1
total_juliaca = data_juliaca['cantidad'].sum()
total_puno = data_puno['cantidad'].sum()

lambda_juliaca = total_juliaca / dias
lambda_puno = total_puno / dias

print(f"\n--- RESULTADOS PARA EL CAPÍTULO IV ---")
print(f"Total delitos Juliaca: {total_juliaca}")
print(f"Total delitos Puno: {total_puno}")
print(f"Lambda Juliaca (λ promedio diario): {lambda_juliaca:.4f}")
print(f"Lambda Puno (λ promedio diario): {lambda_puno:.4f}")

# 4. Cálculo de Probabilidad (Ejemplo: Probabilidad de que ocurran exactamente 5 delitos)
if lambda_juliaca > 0:
    prob_5_juliaca = poisson.pmf(5, lambda_juliaca)
    print(f"Probabilidad de exactamente 5 delitos en Juliaca: {prob_5_juliaca * 100:.2f}%")
else:
    print("⚠️ No se pudo calcular probabilidad porque Lambda es 0. Revisa el nombre del archivo.")




