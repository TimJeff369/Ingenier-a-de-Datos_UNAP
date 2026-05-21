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
    """
    df = pd.read_csv('datos.csv', encoding='latin-1', sep=';')
    
    # Seleccionar las columnas solicitadas
    columnas_necesarias = ['DPTO_HECHO', 'PROV_HECHO', 'DIST_HECHO', 'UBIGEO_HECHO',
                           'Denuncias_2017', 'Denuncias_2018', 'Denuncias_2019']
    
    # Filtrar solo las columnas que existan en el CSV para evitar errores
    columnas_disponibles = [col for col in columnas_necesarias if col in df.columns]
    df = df[columnas_disponibles]

    # Limpiar datos numéricos
    for col in ['Denuncias_2017', 'Denuncias_2018', 'Denuncias_2019']:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0)
    
    # Crear columna de total histórico
    df['Total_Denuncias'] = df.get('Denuncias_2017', 0) + df.get('Denuncias_2018', 0) + df.get('Denuncias_2019', 0)

    # Transformación de datos (Melt) para series temporales
    df_melt = pd.melt(df, id_vars=['DPTO_HECHO', 'PROV_HECHO', 'DIST_HECHO'], 
                      value_vars=['Denuncias_2017', 'Denuncias_2018', 'Denuncias_2019'],
                      var_name='Año', value_name='Denuncias')
    
    df_melt['Año'] = df_melt['Año'].str.replace('Denuncias_', '').astype(int)

    return df, df_melt

# Carga de datos inicial
try:
    df_completo, df_melt_completo = cargar_datos()
except Exception as e:
    st.error(f"Error al cargar el archivo 'datos.csv'. Detalle técnico: {e}")
    st.stop()


# --- BARRA LATERAL (SIDEBAR) JERÁRQUICA ---
st.sidebar.header("Filtros Geográficos")
st.sidebar.markdown("Selecciona la ubicación para actualizar los análisis:")

# 1. Filtro Región (Departamento)
lista_regiones = sorted(df_completo['DPTO_HECHO'].dropna().astype(str).unique().tolist())
idx_puno = lista_regiones.index('PUNO') if 'PUNO' in lista_regiones else 0
dpto_sel = st.sidebar.selectbox("1. Región (DPTO_HECHO)", lista_regiones, index=idx_puno)

# Datos filtrados por la región seleccionada
df_dpto = df_completo[df_completo['DPTO_HECHO'] == dpto_sel]

# 2. Filtro Provincia
lista_provincias = ['TODAS'] + sorted(df_dpto['PROV_HECHO'].dropna().astype(str).unique().tolist())
prov_sel = st.sidebar.selectbox("2. Provincia (PROV_HECHO)", lista_provincias)

# Datos filtrados por la provincia seleccionada
if prov_sel != 'TODAS':
    df_prov = df_dpto[df_dpto['PROV_HECHO'] == prov_sel]
else:
    df_prov = df_dpto

# 3. Filtro Distrito
lista_distritos = ['TODOS'] + sorted(df_prov['DIST_HECHO'].dropna().astype(str).unique().tolist())
dist_sel = st.sidebar.selectbox("3. Distrito (DIST_HECHO)", lista_distritos)


# --- LÓGICA DE SEPARACIÓN (SELECCIÓN vs LOS DEMÁS) ---
if prov_sel == 'TODAS':
    df_seleccion = df_dpto
    df_resto = pd.DataFrame() # No hay "demás" si se selecciona toda la región
    titulo_sel = f"Región: {dpto_sel}"
    titulo_resto = "No aplica (Toda la región seleccionada)"
elif dist_sel == 'TODOS':
    df_seleccion = df_prov
    df_resto = df_dpto[df_dpto['PROV_HECHO'] != prov_sel]
    titulo_sel = f"Provincia: {prov_sel}"
    titulo_resto = f"Otras Provincias en {dpto_sel}"
else:
    df_seleccion = df_prov[df_prov['DIST_HECHO'] == dist_sel]
    df_resto = df_prov[df_prov['DIST_HECHO'] != dist_sel]
    titulo_sel = f"Distrito: {dist_sel}"
    titulo_resto = f"Otros Distritos en {prov_sel}"

# Data derretida (Melt) correspondiente a la selección
df_melt_seleccion = df_melt_completo[df_melt_completo.set_index(['DPTO_HECHO', 'PROV_HECHO', 'DIST_HECHO']).index.isin(df_seleccion.set_index(['DPTO_HECHO', 'PROV_HECHO', 'DIST_HECHO']).index)]
df_melt_resto = df_melt_completo[df_melt_completo.set_index(['DPTO_HECHO', 'PROV_HECHO', 'DIST_HECHO']).index.isin(df_resto.set_index(['DPTO_HECHO', 'PROV_HECHO', 'DIST_HECHO']).index)]


# --- INICIO DE LA INTERFAZ PRINCIPAL ---
st.title("Sistema de Análisis y Predicción de Riesgo Delictivo")
st.markdown("Esta plataforma visualiza la incidencia delictiva y aplica el **Modelo Probabilístico de Poisson** para evaluar el riesgo, estructurada como resultado práctico de la monografía de investigación.")

tab1, tab2, tab3 = st.tabs(["Análisis de la Selección", "Comparativa con el Entorno (Los Demás)", "Modelo Probabilístico (Poisson)"])

# ---------------------------------------------------------
# PESTAÑA 1: DATOS DE LA ZONA SELECCIONADA
# ---------------------------------------------------------
with tab1:
    st.header(f"Análisis Aislado: {titulo_sel}")
    st.markdown("Cálculos y gráficos generados exclusivamente para los filtros aplicados en el panel izquierdo.")
    
    col1, col2 = st.columns([1, 2])
    
    with col1:
        st.subheader("Métricas Totales")
        total_historico = int(df_seleccion['Total_Denuncias'].sum())
        st.metric("Total Denuncias (2017-2019)", total_historico)
        st.dataframe(df_seleccion[['DIST_HECHO', 'Total_Denuncias']].head(10), use_container_width=True)

    with col2:
        st.subheader("Evolución Temporal")
        tendencia_sel = df_melt_seleccion.groupby('Año')['Denuncias'].sum().reset_index()
        fig1, ax1 = plt.subplots(figsize=(8, 4))
        sns.lineplot(data=tendencia_sel, x='Año', y='Denuncias', marker='o', ax=ax1, color='#1f77b4', linewidth=2.5)
        ax1.set_xticks([2017, 2018, 2019])
        ax1.set_title("Línea de Tiempo de Denuncias", fontsize=12)
        st.pyplot(fig1)

# ---------------------------------------------------------
# PESTAÑA 2: COMPARATIVA CON "LOS DEMÁS"
# ---------------------------------------------------------
with tab2:
    st.header(f"Contraste: {titulo_sel} vs {titulo_resto}")
    
    if df_resto.empty:
        st.info("Seleccione una provincia o distrito en el panel lateral para activar la comparativa con su entorno.")
    else:
        st.markdown(f"Visualización del comportamiento delictivo en las zonas adyacentes (**{titulo_resto}**).")
        
        # Comparativa de Totales
        total_resto = int(df_resto['Total_Denuncias'].sum())
        
        fig2, ax2 = plt.subplots(figsize=(10, 5))
        datos_comparativos = pd.DataFrame({
            'Zona': [titulo_sel, titulo_resto],
            'Total Denuncias': [total_historico, total_resto]
        })
        sns.barplot(data=datos_comparativos, x='Zona', y='Total Denuncias', palette='Reds_d', ax=ax2)
        ax2.set_title("Volumen Histórico: Selección vs Entorno (2017-2019)")
        st.pyplot(fig2)

        st.subheader("Detalle de las Zonas Restantes")
        st.dataframe(df_resto[['PROV_HECHO', 'DIST_HECHO', 'Total_Denuncias']].sort_values(by='Total_Denuncias', ascending=False).head(15), use_container_width=True)

# ---------------------------------------------------------
# PESTAÑA 3: MODELO PROBABILÍSTICO DE POISSON
# ---------------------------------------------------------
with tab3:
    st.header("Teoría de Probabilidades: Distribución de Poisson")
    
    # Calcular Poisson basado en la selección actual
    if total_historico > 0:
        # Lambda = Promedio de denuncias por año de la selección
        lambda_delitos = total_historico / 3
        
        st.markdown(f"Aplicando el modelo probabilístico para **{titulo_sel}**.")
        
        colA, colB = st.columns([1, 2])
        
        with colA:
            st.metric(label="Tasa Media (λ) - Denuncias/Año", value=f"{lambda_delitos:.2f}")
            
            k_eventos = st.number_input(f"Calcular probabilidad de que ocurran exactamente 'k' delitos el próximo año:", min_value=0, value=int(lambda_delitos), step=1)
            probabilidad_k = poisson.pmf(k_eventos, lambda_delitos)
            st.success(f"Probabilidad P(X = {k_eventos}): **{probabilidad_k:.4%}**")
            
        with colB:
            x_vals = np.arange(0, int(lambda_delitos * 2.5) + 5)
            y_vals = poisson.pmf(x_vals, lambda_delitos)
            
            fig3, ax3 = plt.subplots(figsize=(8, 4))
            ax3.bar(x_vals, y_vals, color='#ff7f0e', alpha=0.7)
            ax3.plot(x_vals, y_vals, marker='o', color='red', linestyle='--', alpha=0.5)
            
            ax3.set_title(f"Distribución de Poisson (λ={lambda_delitos:.2f})")
            ax3.set_xlabel("Número de Denuncias (k)")
            ax3.set_ylabel("Probabilidad P(X=k)")
            
            if k_eventos in x_vals:
                ax3.bar(k_eventos, y_vals[k_eventos], color='red')
                
            st.pyplot(fig3)
    else:
        st.warning("No hay suficientes datos históricos en la zona seleccionada para calcular la distribución de Poisson (λ = 0).")


        