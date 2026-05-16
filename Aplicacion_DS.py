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

# El resto de tu código sigue igual...
st.title("🛡️ Sistema Predictivo de Inseguridad - Región Puno")



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