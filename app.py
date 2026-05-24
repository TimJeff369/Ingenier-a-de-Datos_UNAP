import streamlit as st
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
from scipy.stats import poisson

import plotly.express as px
import json

import sqlite3
import hashlib

# Configuración de la página (Experiencia de Usuario UX - Cap 2.5)
st.set_page_config(page_title="Dashboard Delictivo - Región Puno", layout="wide")

# Estilo profesional para gráficos
sns.set_palette("muted")



# =====================================================================
# --- INYECCIÓN DE ESTILO VISUAL (Para impresionar al jurado) ---
# Se extrae la identidad visual de la imagen de cabecera proporcionada:
# - Fondo: Gradiente Azul medianoche a Navy
# - Texto Primario: Dorado brillante
# - Tipografía: Rajdhani (estilo tecnológico)
# - Acentos: Cian/Teal claro
# =====================================================================

# 1. Cargar la fuente Rajdhani desde Google Fonts
st.markdown('<link href="https://fonts.googleapis.com/css2?family=Rajdhani:wght@500;600;700&display=swap" rel="stylesheet">', unsafe_allow_html=True)

# 2. Aplicar CSS global para la app
st.markdown("""
    <style>
        /* Tipografía y fondo para toda la página */
        [data-testid="stAppViewContainer"] {
            background: linear-gradient(135deg, #0a0e27 0%, #172a5a 100%);
            color: #ffd700; /* Texto dorado por defecto */
            font-family: 'Rajdhani', sans-serif;
        }
        
        /* Asegurar que los títulos sean dorados y con la fuente */
        .stMarkdown h1, .stMarkdown h2, .stMarkdown h3, .stMarkdown h4 {
            color: #ffd700 !important;
            font-family: 'Rajdhani', sans-serif !important;
            text-shadow: 0px 0px 5px rgba(255, 215, 0, 0.3); /* Un sutil brillo dorado */
        }
        
        /* Darle un tono más acorde al "Sidebar" (barra lateral) */
        [data-testid="stSidebar"] {
            background-color: rgba(10, 14, 39, 0.8) !important;
            border-right: 1px solid #1ed7fe; /* Un borde cian claro */
        }
        [data-testid="stSidebar"] p, [data-testid="stSidebar"] label {
            color: #1ed7fe !important; /* Texto de etiquetas en cian */
        }

        /* Ocultar el header superior por defecto para un look más "full app" */
        [data-testid="stHeader"] {
            background-color: rgba(0,0,0,0);
        }
    </style>
""", unsafe_allow_html=True)






# --- SISTEMA DE AUTENTICACIÓN Y BASE DE DATOS ---

def inicializar_bd():
    """Crea la tabla de usuarios si no existe"""
    conn = sqlite3.connect('usuarios.db')
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS usuarios
                 (email TEXT PRIMARY KEY, password TEXT)''')
    conn.commit()
    conn.close()

def encriptar_password(password):
    """Convierte la contraseña en un hash seguro (¡Para impresionar a la profesora!)"""
    return hashlib.sha256(password.encode()).hexdigest()

def registrar_usuario(email, password):
    """Valida el correo y guarda el nuevo usuario en SQLite"""
    if not email.endswith("@gmail.data.sience.edu.pe"):
        return False, "El correo electrónico debe terminar obligatoriamente en @gmail.data.sience.edu.pe"
    
    try:
        conn = sqlite3.connect('usuarios.db')
        c = conn.cursor()
        # Guardamos el email y la contraseña encriptada
        c.execute("INSERT INTO usuarios (email, password) VALUES (?, ?)", (email, encriptar_password(password)))
        conn.commit()
        conn.close()
        return True, "¡Registro exitoso! Ahora puedes iniciar sesión en la pestaña de al lado."
    except sqlite3.IntegrityError:
        return False, "Este correo ya se encuentra registrado en el sistema."

def verificar_login(email, password):
    """Comprueba si el usuario y la contraseña coinciden en la base de datos"""
    conn = sqlite3.connect('usuarios.db')
    c = conn.cursor()
    c.execute("SELECT password FROM usuarios WHERE email=?", (email,))
    resultado = c.fetchone()
    conn.close()
    
    # Comparamos el hash guardado con el hash de la contraseña ingresada
    if resultado and resultado[0] == encriptar_password(password):
        return True
    return False

# Inicializar la base de datos al arrancar la app
inicializar_bd()

# Variable de estado (Session State) para saber si el usuario ya entró
if 'autenticado' not in st.session_state:
    st.session_state['autenticado'] = False










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
    # FIX: Se crea un DataFrame vacío, pero heredando las columnas para que Pandas no falle
    df_resto = pd.DataFrame(columns=df_completo.columns) 
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

# FIX: Comprobación de seguridad. Si no hay "resto", no intentamos hacer el set_index
if df_resto.empty:
    df_melt_resto = pd.DataFrame(columns=df_melt_completo.columns)
else:
    df_melt_resto = df_melt_completo[df_melt_completo.set_index(['DPTO_HECHO', 'PROV_HECHO', 'DIST_HECHO']).index.isin(df_resto.set_index(['DPTO_HECHO', 'PROV_HECHO', 'DIST_HECHO']).index)]


# --- CONTROL DE ACCESO (LOGIN / REGISTRO) ---
if not st.session_state['autenticado']:
    st.title("🔒 Portal de Acceso Restringido")
    st.markdown("Sistema de Análisis de Riesgo Delictivo - **Acceso solo para personal autorizado**.")
    
    # Crear pestañas para el Login y Registro
    tab_login, tab_registro = st.tabs(["🔑 Iniciar Sesión", "📝 Registrar Nuevo Usuario"])
    
    with tab_login:
        st.subheader("Ingreso al Dashboard")
        login_email = st.text_input("Correo Institucional", key="login_email")
        login_password = st.text_input("Contraseña", type="password", key="login_password")
        
        if st.button("Ingresar", type="primary"):
            if verificar_login(login_email, login_password):
                st.session_state['autenticado'] = True
                st.rerun() # Recarga la página para mostrar el dashboard
            else:
                st.error("Credenciales incorrectas. Verifica tu correo y contraseña.")
                
    with tab_registro:
        st.subheader("Solicitar Acceso")
        st.info("Solo se admiten correos con el dominio: @gmail.data.sience.edu.pe")
        reg_email = st.text_input("Nuevo Correo Institucional", key="reg_email")
        reg_password = st.text_input("Nueva Contraseña", type="password", key="reg_password")
        
        if st.button("Registrar Usuario"):
            if reg_email and reg_password:
                exito, mensaje = registrar_usuario(reg_email, reg_password)
                if exito:
                    st.success(mensaje)
                else:
                    st.error(mensaje)
            else:
                st.warning("Por favor, completa ambos campos para registrarte.")
                
    # st.stop() detiene la ejecución aquí si no está autenticado, ocultando el resto del código
    st.stop() 

# Botón para cerrar sesión (Aparecerá en la barra lateral debajo de los filtros)
st.sidebar.markdown("---")
if st.sidebar.button("Cerrar Sesión"):
    st.session_state['autenticado'] = False
    st.rerun()

# =====================================================================
# --- A PARTIR DE AQUÍ VA TU INTERFAZ PRINCIPAL DEL DASHBOARD ---
# =====================================================================

st.title("Sistema de Análisis y Predicción de Riesgo Delictivo")
st.markdown("Esta plataforma visualiza la incidencia delictiva y aplica el **Modelo Probabilístico de Poisson** para evaluar el riesgo, estructurada como resultado práctico de la monografía de investigación.")

tab1, tab2, tab3, tab4 = st.tabs(["Análisis de la Selección", "Comparativa con el Entorno (Los Demás)", "Modelo Probabilístico (Poisson)", "📍 Mapa de Riesgo Nacional"])



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











# ---------------------------------------------------------
# PESTAÑA 4: MAPA COROPLÉTICO NACIONAL (CON NOMBRES ESTÁTICOS Y HOVER ESTILIZADO)
# ---------------------------------------------------------
with tab4:
    st.header("Visualización Cartográfica Nacional - Nivel de Riesgo")
    st.markdown("Este mapa clasifica el riesgo delictivo en tres niveles usando segmentación estadística de percentiles.")

    # 0. Importar librerías necesarias y la fuente Rajdhani
    import plotly.graph_objects as go
    st.markdown('<link href="https://fonts.googleapis.com/css2?family=Rajdhani:wght@600;700&display=swap" rel="stylesheet">', unsafe_allow_html=True)

    try:
        # 1. Cargar el GeoJSON
        with open('peru_departamentos.geojson', 'r', encoding='utf-8') as f:
            geojson_peru = json.load(f)

        # 2. Preparar datos y sumar los totales nacionales
        df_nacional = df_completo.groupby('DPTO_HECHO', as_index=False)['Total_Denuncias'].sum()
        df_nacional['DPTO_HECHO'] = df_nacional['DPTO_HECHO'].str.strip().str.upper()

        # 3. Motor de Clasificación Estadística (Tercios)
        limite_bajo = df_nacional['Total_Denuncias'].quantile(0.33)
        limite_alto = df_nacional['Total_Denuncias'].quantile(0.66)

        def clasificar_riesgo(total):
            if total <= limite_bajo:
                return 'No Peligroso'
            elif total <= limite_alto:
                return 'Poco Peligroso'
            else:
                return 'Muy Peligroso'

        df_nacional['Nivel de Riesgo'] = df_nacional['Total_Denuncias'].apply(clasificar_riesgo)

        # 4. Crear el Mapa Coroplético Base
        fig_mapa = px.choropleth_mapbox(
            df_nacional,
            geojson=geojson_peru,
            locations='DPTO_HECHO',
            featureidkey='properties.NOMBDEP',  
            color='Nivel de Riesgo',            
            color_discrete_map={                
                'No Peligroso': '#2ca02c',      # Verde
                'Poco Peligroso': '#ff7f0e',    # Naranja
                'Muy Peligroso': '#d62728'      # Rojo
            },
            mapbox_style="carto-positron",
            zoom=4.5,
            center={"lat": -9.19, "lon": -75.01},
            opacity=0.75,                       
            hover_name='DPTO_HECHO',            
            hover_data={
                'DPTO_HECHO': False,            
                'Nivel de Riesgo': True,        
                'Total_Denuncias': True         
            }
        )

        # 5. CAPA DE TEXTO ESTÁTICO: Diccionario de coordenadas centrales por departamento
        centroides = {
            'DPTO_HECHO': ['AMAZONAS', 'ANCASH', 'APURIMAC', 'AREQUIPA', 'AYACUCHO', 'CAJAMARCA', 'CALLAO', 'CUSCO', 'HUANCAVELICA', 'HUANUCO', 'ICA', 'JUNIN', 'LA LIBERTAD', 'LAMBAYEQUE', 'LIMA', 'LORETO', 'MADRE DE DIOS', 'MOQUEGUA', 'PASCO', 'PIURA', 'PUNO', 'SAN MARTIN', 'TACNA', 'TUMBES', 'UCAYALI'],
            'lat': [-6.2, -9.5, -14.0, -16.2, -14.2, -6.6, -12.05, -13.5, -12.8, -9.9, -14.1, -11.4, -8.0, -6.7, -12.0, -4.5, -12.0, -16.8, -10.5, -5.2, -15.0, -7.0, -17.5, -3.8, -9.0],
            'lon': [-77.8, -77.5, -72.9, -71.9, -74.1, -78.6, -77.15, -71.9, -75.0, -75.6, -75.6, -74.9, -78.5, -79.9, -76.6, -74.5, -70.5, -71.1, -75.0, -80.5, -70.0, -76.7, -70.3, -80.6, -73.0]
        }
        df_centros = pd.DataFrame(centroides)
        
        # Formatear nombres en negrita para máxima claridad en pantalla
        nombres_negrita = [f"<b>{name}</b>" for name in df_centros['DPTO_HECHO']]

        # Inyectar la capa de texto sobre el mapa coroplético
        fig_mapa.add_trace(go.Scattermapbox(
            lat=df_centros['lat'],
            lon=df_centros['lon'],
            mode='text',
            text=nombres_negrita,
            textposition='center',
            showlegend=False,
            hoverinfo='skip', # Evita que el texto estático interfiera con el cuadro del mouse
            textfont=dict(
                family="Rajdhani, sans-serif",
                size=12,
                color="#0a0e27" # Color azul oscuro de alta densidad para resaltar sobre los polígonos
            )
        ))

        # 6. Configuración de diseño y estilos de la interfaz (HoverBox)
        color_fondo_cuadro = "#0d1b3e"   
        color_letras_oro = "#ffd700"     
        color_borde_cian = "#1ed7fe"     

        fig_mapa.update_traces(marker_line_width=1.5, marker_line_color='black', selector=dict(type='choroplethmapbox'))

        fig_mapa.update_layout(
            margin={"r":0,"t":30,"l":0,"b":0},
            height=650,
            legend_title_text='Categoría de Riesgo',
            
            hoverlabel=dict(
                bgcolor=color_fondo_cuadro,          
                font_size=16,                        
                font_family="Rajdhani, sans-serif",  
                font_color=color_letras_oro,         
                bordercolor=color_borde_cian,        
            )
        )

        # 7. Desplegar gráfico
        st.plotly_chart(fig_mapa, use_container_width=True)

    except Exception as e:
        st.error(f"No se pudo cargar el mapa. Verifica tu archivo GeoJSON. Error técnico: {e}")