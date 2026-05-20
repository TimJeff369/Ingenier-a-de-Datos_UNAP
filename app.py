import streamlit as st
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
from scipy.stats import poisson

# Configuración de la página (Experiencia de Usuario UX - Cap 2.5)
st.set_page_config(page_title="Dashboard Delictivo - Región Puno", layout="wide")

# Estilo profesional para gráficos
plt.style.use('seaborn-v0_8-whitegrid')
sns.set_palette("muted")

@st.cache_data
def cargar_datos():
    """
    Fase de Ingeniería de Datos (Cap 2.1)
    Carga de datos solucionando el UnicodeDecodeError mediante latin-1
    """
    # Leer el dataset, especificando la codificación correcta
    df = pd.read_csv('datos.csv', encoding='latin-1', sep=',') 
    # Nota: Si tu CSV usa punto y coma, cambia sep=',' por sep=';'

    # Seleccionar solo las columnas de interés
    columnas_necesarias = ['DPTO_HECHO', 'PROV_HECHO', 'DIST_HECHO', 
                           'Denuncias_2017', 'Denuncias_2018', 'Denuncias_2019']
    
    # Verificar que las columnas existan, si hay diferencias de espacios, limpiar nombres
    df.columns = df.columns.str.strip()
    df = df[columnas_necesarias]

    # Limpiar datos numéricos (convertir a float y llenar nulos con 0)
    for col in ['Denuncias_2017', 'Denuncias_2018', 'Denuncias_2019']:
        df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0)
    
    # Crear columna de total histórico
    df['Total_Denuncias'] = df['Denuncias_2017'] + df['Denuncias_2018'] + df['Denuncias_2019']

    # Transformación de datos (Melt) para series temporales
    df_melt = pd.melt(df, id_vars=['DPTO_HECHO', 'PROV_HECHO', 'DIST_HECHO'], 
                      value_vars=['Denuncias_2017', 'Denuncias_2018', 'Denuncias_2019'],
                      var_name='Año', value_name='Denuncias')
    
    # Limpiar el texto del año para que solo sea el número
    df_melt['Año'] = df_melt['Año'].str.replace('Denuncias_', '').astype(int)

    return df, df_melt

# --- INICIO DE LA INTERFAZ ---
st.title("Sistema de Análisis y Predicción de Riesgo Delictivo")
st.markdown("""
Esta plataforma visualiza la incidencia delictiva y aplica el **Modelo Probabilístico de Poisson** para evaluar el riesgo en diferentes jurisdicciones, con énfasis en el eje Puno - Juliaca - Azángaro.
""")

# Carga de datos
try:
    df, df_melt = cargar_datos()
    
    # Filtrar solo la región Puno para el análisis local
    df_puno = df[df['DPTO_HECHO'].str.upper() == 'PUNO']
    df_melt_puno = df_melt[df_melt['DPTO_HECHO'].str.upper() == 'PUNO']

    if df_puno.empty:
        st.warning("No se encontraron registros para el departamento de PUNO en el dataset.")
        st.stop()

except Exception as e:
    st.error(f"Error al cargar el archivo 'datos.csv'. Verifica que el archivo esté en la misma carpeta. Detalle técnico: {e}")
    st.stop()


# --- PESTAÑAS DE NAVEGACIÓN ---
tab1, tab2, tab3 = st.tabs(["Comparativa Estratégica (Puno-Juliaca-Azángaro)", "Análisis Exploratorio General", "Modelo Probabilístico (Poisson)"])

# ---------------------------------------------------------
# PESTAÑA 1: COMPARATIVA ESTRATÉGICA (Cap 4.3 de la Monografía)
# ---------------------------------------------------------
with tab1:
    st.header("Análisis Comparativo del Eje Principal")
    st.markdown("Comparativa específica entre la capital departamental (Puno), el principal centro comercial (Juliaca - Prov. San Román) y Azángaro.")
    
    # Filtrar datos específicos de estas zonas
    # Asumimos Juliaca como distrito dentro de San Román
    condicion_zonas = (
        (df_puno['PROV_HECHO'].str.upper() == 'PUNO') | 
        (df_puno['PROV_HECHO'].str.upper() == 'AZANGARO') | 
        (df_puno['PROV_HECHO'].str.upper() == 'SAN ROMAN')
    )
    df_zonas = df_puno[condicion_zonas].groupby('PROV_HECHO')[['Denuncias_2017', 'Denuncias_2018', 'Denuncias_2019']].sum().reset_index()
    
    # Gráfica de barras comparativa
    fig, ax = plt.subplots(figsize=(10, 5))
    df_zonas_melt = pd.melt(df_zonas, id_vars='PROV_HECHO', var_name='Año', value_name='Total Denuncias')
    df_zonas_melt['Año'] = df_zonas_melt['Año'].str.replace('Denuncias_', '')
    
    sns.barplot(data=df_zonas_melt, x='PROV_HECHO', y='Total Denuncias', hue='Año', ax=ax, palette='Blues_d')
    ax.set_title("Evolución de Denuncias (2017-2019): Puno vs San Román vs Azángaro", fontsize=14)
    ax.set_xlabel("Provincia")
    ax.set_ylabel("Número de Denuncias")
    
    st.pyplot(fig)
    
    # Datos específicos de Juliaca (Distrito)
    juliaca_datos = df_puno[df_puno['DIST_HECHO'].str.upper() == 'JULIACA'][['Denuncias_2017', 'Denuncias_2018', 'Denuncias_2019']].sum()
    st.info(f"**Nota:** Analizando específicamente a nivel distrital, **Juliaca** registró {int(juliaca_datos.sum())} denuncias en el periodo 2017-2019.")

# ---------------------------------------------------------
# PESTAÑA 2: ANÁLISIS EXPLORATORIO GENERAL
# ---------------------------------------------------------
with tab2:
    st.header("Filtros de Análisis Regional")
    col1, col2 = st.columns(2)
    
    provincias_lista = sorted(df_puno['PROV_HECHO'].dropna().unique().tolist())
    
    with col1:
        prov_seleccionada = st.selectbox("Seleccione una Provincia:", ['TODAS'] + provincias_lista)
    
    if prov_seleccionada != 'TODAS':
        df_filtrado = df_puno[df_puno['PROV_HECHO'] == prov_seleccionada]
        df_melt_filtrado = df_melt_puno[df_melt_puno['PROV_HECHO'] == prov_seleccionada]
        distritos_lista = sorted(df_filtrado['DIST_HECHO'].dropna().unique().tolist())
        with col2:
            dist_seleccionado = st.selectbox("Seleccione un Distrito:", ['TODOS'] + distritos_lista)
            if dist_seleccionado != 'TODOS':
                df_filtrado = df_filtrado[df_filtrado['DIST_HECHO'] == dist_seleccionado]
                df_melt_filtrado = df_melt_filtrado[df_melt_filtrado['DIST_HECHO'] == dist_seleccionado]
    else:
        df_filtrado = df_puno
        df_melt_filtrado = df_melt_puno
        with col2:
            st.write("") # Espacio vacío
            
    st.subheader("Resumen de Denuncias (Selección)")
    st.dataframe(df_filtrado.drop(columns=['DPTO_HECHO', 'Total_Denuncias']), use_container_width=True)
    
    # Gráfico de tendencia temporal
    tendencia = df_melt_filtrado.groupby('Año')['Denuncias'].sum().reset_index()
    fig2, ax2 = plt.subplots(figsize=(10, 4))
    sns.lineplot(data=tendencia, x='Año', y='Denuncias', marker='o', ax=ax2, color='#1f77b4', linewidth=2.5)
    ax2.set_xticks([2017, 2018, 2019])
    ax2.set_title("Línea de Tiempo de Denuncias", fontsize=14)
    st.pyplot(fig2)

# ---------------------------------------------------------
# PESTAÑA 3: MODELO PROBABILÍSTICO DE POISSON (Cap 2.2 y 4.1)
# ---------------------------------------------------------
with tab3:
    st.header("Teoría de Probabilidades: Distribución de Poisson")
    st.markdown("""
    La **Distribución de Poisson** es ideal para modelar el número de eventos (delitos) que ocurren en un intervalo de tiempo fijo, 
    conociendo una tasa media de ocurrencia (λ - lambda).
    """)
    
    st.subheader("Simulador de Riesgo por Distrito")
    
    # Selección para el modelo
    distrito_poisson = st.selectbox("Seleccione un distrito para aplicar el modelo probabilístico:", 
                                    sorted(df_puno['DIST_HECHO'].dropna().unique().tolist()))
    
    # Cálculos
    datos_dist = df_puno[df_puno['DIST_HECHO'] == distrito_poisson]
    total_3_anios = datos_dist[['Denuncias_2017', 'Denuncias_2018', 'Denuncias_2019']].sum().sum()
    
    # Lambda = Promedio de denuncias por año
    lambda_delitos = total_3_anios / 3
    
    colA, colB = st.columns([1, 2])
    
    with colA:
        st.metric(label="Tasa Media (λ) - Denuncias/Año", value=f"{lambda_delitos:.2f}")
        st.write(f"Basado en el histórico, se espera un promedio de **{lambda_delitos:.1f}** denuncias anuales en {distrito_poisson}.")
        
        # Interacción de usuario para predecir 'k' eventos
        k_eventos = st.number_input(f"Calcular probabilidad de que ocurran exactamente 'k' delitos en el próximo año:", min_value=0, value=int(lambda_delitos), step=1)
        probabilidad_k = poisson.pmf(k_eventos, lambda_delitos)
        st.success(f"Probabilidad P(X = {k_eventos}): **{probabilidad_k:.4%}**")
        
    with colB:
        # Gráfica de la PMF (Probability Mass Function) de Poisson
        if lambda_delitos > 0:
            x_vals = np.arange(0, int(lambda_delitos * 2.5) + 5)
            y_vals = poisson.pmf(x_vals, lambda_delitos)
            
            fig3, ax3 = plt.subplots(figsize=(8, 4))
            ax3.bar(x_vals, y_vals, color='#ff7f0e', alpha=0.7)
            ax3.plot(x_vals, y_vals, marker='o', color='red', linestyle='--', alpha=0.5)
            
            ax3.set_title(f"Distribución de Poisson para {distrito_poisson} (λ={lambda_delitos:.2f})")
            ax3.set_xlabel("Número de Denuncias (k)")
            ax3.set_ylabel("Probabilidad P(X=k)")
            
            # Resaltar la barra seleccionada por el usuario
            if k_eventos in x_vals:
                ax3.bar(k_eventos, y_vals[k_eventos], color='red')
                
            st.pyplot(fig3)
        else:
            st.warning("No hay datos suficientes para generar la distribución (λ = 0).")
            