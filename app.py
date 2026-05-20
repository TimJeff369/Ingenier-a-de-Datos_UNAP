import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from scipy.stats import poisson
import numpy as np

# =====================================================================
# --- 1. CONFIGURACIÓN DE LA PÁGINA (Arquitectura UX - Cap 2.5) ---
# =====================================================================
st.set_page_config(page_title="Dashboard Predictivo Puno - UNA", layout="wide")

st.title("📊 Sistema de Visualización de Riesgo Delictivo")
st.markdown("""
**Universidad Nacional del Altiplano - Ingeniería de Datos**
*Aplicación de Ingeniería de Datos y Modelos Probabilísticos mediante Tecnologías Cloud.*
""")

# =====================================================================
# --- 2. INGENIERÍA DE DATOS (Ingesta y Limpieza - Cap 2.1 y 4.1) ---
# =====================================================================
@st.cache_data
def cargar_datos():
    try:
        # Lectura robusta del archivo principal (Open Data)
        df = pd.read_csv("datos.csv", encoding='latin-1', on_bad_lines='skip', sep=None, engine='python')
        df.columns = df.columns.str.strip() # Quitar espacios
        
        # Transformación (Melt) si los años están en columnas horizontales
        if 'Año' not in df.columns:
            columnas_fijas = [col for col in df.columns if not col.isdigit()]
            columnas_anios = [col for col in df.columns if col.isdigit()]
            if len(columnas_anios) > 0:
                df = pd.melt(df, id_vars=columnas_fijas, value_vars=columnas_anios, var_name='Año', value_name='Denuncias')
            else:
                df['Año'] = '2019'
                if 'Denuncias' not in df.columns: df['Denuncias'] = 1

        # Asegurar que las Denuncias sean números enteros para el modelo probabilístico
        df['Denuncias'] = pd.to_numeric(df['Denuncias'], errors='coerce').fillna(0)
        
        # Normalizar nombres de ubicación para evitar errores en los filtros
        for col in ['DPTO_HECHO', 'PROV_HECHO', 'DIST_HECHO']:
            if col in df.columns:
                df[col] = df[col].astype(str).str.strip().str.upper()
                
        return df
    except Exception as e:
        st.error(f"Error en la ingesta de datos: {e}")
        return pd.DataFrame()

# Ejecutamos la carga de datos
df_crimen = cargar_datos()

if not df_crimen.empty and 'DPTO_HECHO' in df_crimen.columns:
    
    # =====================================================================
    # --- 3. BARRA LATERAL (Filtros en Cascada Dinámicos) ---
    # =====================================================================
    st.sidebar.header("Parámetros de Consulta")
    st.sidebar.markdown("Filtros espaciales interactivos")
    
    # Filtro 1: Región (Departamento)
    regiones = sorted(df_crimen['DPTO_HECHO'].unique().tolist())
    idx_puno = regiones.index('PUNO') if 'PUNO' in regiones else 0
    region_sel = st.sidebar.selectbox("1. Seleccione Región:", regiones, index=idx_puno)

    # Filtro 2: Provincia (Se actualiza según la Región)
    df_region = df_crimen[df_crimen['DPTO_HECHO'] == region_sel]
    provincias = sorted(df_region['PROV_HECHO'].unique().tolist())
    idx_sanroman = provincias.index('SAN ROMAN') if 'SAN ROMAN' in provincias else (provincias.index('PUNO') if 'PUNO' in provincias else 0)
    provincia_sel = st.sidebar.selectbox("2. Seleccione Provincia:", provincias, index=idx_sanroman)

    # Filtro 3: Distrito (Se actualiza según la Provincia)
    df_prov = df_region[df_region['PROV_HECHO'] == provincia_sel]
    distritos = sorted(df_prov['DIST_HECHO'].unique().tolist())
    distrito_sel = st.sidebar.selectbox("3. Seleccione Distrito:", distritos)
    
    # Dataframe final completamente filtrado para el modelo
    df_dist = df_prov[df_prov['DIST_HECHO'] == distrito_sel]

    # =====================================================================
    # --- 4. ANÁLISIS COMPARATIVO Y SERIES TEMPORALES (Cap 2.4 y 4.3) ---
    # =====================================================================
    st.header(f"📈 1. Análisis Comparativo: Provincia de {provincia_sel}")
    st.markdown("Evaluación de series temporales y concentración de incidencias a nivel provincial.")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.write(f"**Evolución Histórica ({provincia_sel})**")
        df_prov_evol = df_prov.groupby('Año')['Denuncias'].sum().reset_index()
        fig_line = px.line(df_prov_evol, x='Año', y='Denuncias', markers=True,
                           title="Análisis de Serie Temporal",
                           color_discrete_sequence=['#FF4B4B'])
        st.plotly_chart(fig_line, use_container_width=True)
        
    with col2:
        st.write(f"**Minería de Datos: Top Distritos ({provincia_sel})**")
        df_prov_dist = df_prov.groupby('DIST_HECHO')['Denuncias'].sum().reset_index()
        df_prov_dist = df_prov_dist.sort_values(by='Denuncias', ascending=False).head(10)
        fig_bar = px.bar(df_prov_dist, x='DIST_HECHO', y='Denuncias', color='Denuncias',
                         color_continuous_scale='Reds', title="Concentración Delictiva")
        st.plotly_chart(fig_bar, use_container_width=True)

    st.markdown("---")

    # =====================================================================
    # --- 5. MODELO PROBABILÍSTICO PREDICTIVO (Cap 2.2 y 4.1) ---
    # =====================================================================
    st.header(f"🧮 2. Modelo Predictivo (Poisson): Distrito {distrito_sel}")
    st.markdown("Despliegue del algoritmo predictivo basado en la Teoría de Probabilidades.")

    if not df_dist.empty:
        # Sumamos las denuncias por año para el distrito seleccionado
        df_dist_evol = df_dist.groupby('Año')['Denuncias'].sum().reset_index()
        
        # Cálculo del parámetro Lambda (Promedio histórico)
        lambda_param = df_dist_evol['Denuncias'].mean()
        
        col_izq, col_der = st.columns([1, 2])
        
        with col_izq:
            st.info(f"**Parámetro Lambda (λ):**\nTasa media histórica de **{lambda_param:.2f}** denuncias anuales en {distrito_sel}.")
            
            if lambda_param > 0:
                st.write("### Simulador de Riesgo")
                k_val = st.number_input("Eventos a predecir (k):", min_value=0, value=int(lambda_param), step=1)
                
                # Fórmula de Poisson
                probabilidad = poisson.pmf(k_val, lambda_param) * 100 
                st.metric(label=f"Probabilidad de exactamente {k_val} incidentes:", value=f"{probabilidad:.2f} %")
                
                # Probabilidad acumulada (Riesgo alto)
                prob_acumulada = (1 - poisson.cdf(k_val - 1, lambda_param)) * 100 if k_val > 0 else 100
                st.metric(label=f"Probabilidad de {k_val} o más incidentes:", value=f"{prob_acumulada:.2f} %")
            else:
                st.warning("No hay suficientes denuncias registradas para calcular el modelo.")
        
        with col_der:
            if lambda_param > 0:
                st.write("**Curva de Distribución de Probabilidades**")
                # Generar valores en X para la curva (hasta 2.5 veces la media para visualizar bien la cola)
                x_vals = np.arange(0, int(lambda_param * 2.5) + 5)
                y_vals = poisson.pmf(x_vals, lambda_param)
                
                fig_poisson = go.Figure(data=[go.Bar(x=x_vals, y=y_vals, marker_color='indigo')])
                fig_poisson.update_layout(
                    xaxis_title="Número de Denuncias Proyectadas (k)", 
                    yaxis_title="Probabilidad (0 a 1)",
                    margin={"r":0,"t":30,"l":0,"b":0}
                )
                st.plotly_chart(fig_poisson, use_container_width=True)
                
        # (Opcional) Expander para ver los datos crudos, útil para validación técnica (Cap 4.4)
        with st.expander(f"Consultar Registros Históricos ({distrito_sel})"):
            st.dataframe(df_dist_evol)
    else:
        st.warning(f"No se encontraron registros de datos para el distrito {distrito_sel}.")

else:
    st.error("Error crítico: El archivo de datos no contiene la estructura requerida (Columnas DPTO_HECHO, PROV_HECHO, DIST_HECHO).")