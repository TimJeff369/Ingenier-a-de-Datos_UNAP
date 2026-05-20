import streamlit as st
import pandas as pd
import plotly.express as px

# --- CONFIGURACIÓN ---
st.set_page_config(page_title="Dashboard Criminal Puno", layout="wide")
st.title("📊 Sistema de Inteligencia Territorial Criminal")
st.markdown("Análisis de criminalidad simplificado y mapa de puntos calientes.")

try:
    # --- 1. LECTURA DE DATOS SEGURA ---
    # Leemos solo el archivo principal de crímenes (el que sabemos que funciona)
    df_crimen = pd.read_csv("datos.csv", encoding='latin-1', on_bad_lines='skip', sep=None, engine='python')
    df_crimen.columns = df_crimen.columns.str.strip() # Limpiamos espacios ocultos
    
    # Arreglamos las columnas si el año está distribuido en varias (Melt)
    if 'Año' not in df_crimen.columns:
        columnas_fijas = [col for col in df_crimen.columns if not col.isdigit()]
        columnas_anios = [col for col in df_crimen.columns if col.isdigit()]
        if len(columnas_anios) > 0:
            df_crimen = pd.melt(df_crimen, id_vars=columnas_fijas, value_vars=columnas_anios, var_name='Año', value_name='Denuncias')
    
    # Aseguramos que las denuncias sean números
    if 'Denuncias' in df_crimen.columns:
        df_crimen['Denuncias'] = pd.to_numeric(df_crimen['Denuncias'], errors='coerce').fillna(0)
    else:
        df_crimen['Denuncias'] = 1 # Por si acaso no existe la columna

    st.success("✅ Archivo de datos procesado con éxito.")

    # --- 2. GRÁFICOS QUE YA FUNCIONABAN ---
    if 'PROV_HECHO' in df_crimen.columns:
        col1, col2 = st.columns(2)
        
        # Agrupamos los datos por provincia
        df_agrupado = df_crimen.groupby('PROV_HECHO')['Denuncias'].sum().reset_index()
        df_top = df_agrupado.sort_values(by='Denuncias', ascending=False).head(10)

        with col1:
            st.subheader("📈 Top Provincias con más Denuncias")
            fig_bar = px.bar(df_top, x='PROV_HECHO', y='Denuncias', color='Denuncias', 
                             color_continuous_scale='Reds', title="Acumulado por Provincia")
            st.plotly_chart(fig_bar, use_container_width=True)
            
        with col2:
            st.subheader("📋 Vista de Datos Crudos")
            st.dataframe(df_top, height=350)

        # --- 3. EL MAPA SIMPLE Y NOVEDOSO (SIN ERRORES) ---
        st.markdown("---")
        st.subheader("🗺️ Cartografía Dinámica: Puntos Calientes (Hotspots)")
        
        # Diccionario "salvavidas" con coordenadas exactas de las provincias de Puno
        # Esto evita que necesites el archivo GeoJSON o el cruce de datos que fallaba
        coordenadas_puno = {
            'PUNO': {'lat': -15.8402, 'lon': -70.0218},
            'SAN ROMAN': {'lat': -15.4967, 'lon': -70.1333}, # Juliaca
            'AZANGARO': {'lat': -14.9080, 'lon': -70.1956},
            'CHUCUITO': {'lat': -16.2133, 'lon': -69.4594},
            'EL COLLAO': {'lat': -16.0886, 'lon': -69.6583},
            'MELGAR': {'lat': -14.8819, 'lon': -70.5897},
            'CARABAYA': {'lat': -14.0667, 'lon': -70.4333},
            'SANDIA': {'lat': -14.3167, 'lon': -69.4667},
            'SAN ANTONIO DE PUTINA': {'lat': -14.9167, 'lon': -69.8667},
            'YUNGUYO': {'lat': -16.2500, 'lon': -69.0833},
            'HUANCANE': {'lat': -15.2000, 'lon': -69.7500},
            'LAMPA': {'lat': -15.3500, 'lon': -70.3667},
            'MOHO': {'lat': -15.3667, 'lon': -69.5000}
        }
        
        # Convertimos el diccionario en un DataFrame temporal
        df_coords = pd.DataFrame.from_dict(coordenadas_puno, orient='index').reset_index()
        df_coords.columns = ['PROV_HECHO', 'lat', 'lon']
        
        # Unimos tus denuncias reales con nuestras coordenadas seguras
        df_mapa = pd.merge(df_agrupado, df_coords, on='PROV_HECHO', how='inner')
        
        if not df_mapa.empty:
            # Creamos un mapa de dispersión profesional (estilo oscuro)
            fig_mapa = px.scatter_mapbox(
                df_mapa, 
                lat="lat", 
                lon="lon", 
                color="Denuncias",
                size="Denuncias", # Las burbujas crecen si hay más crímenes
                hover_name="PROV_HECHO", 
                hover_data={"lat": False, "lon": False, "Denuncias": True},
                color_continuous_scale=px.colors.sequential.YlOrRd,
                size_max=50,
                zoom=6.5, 
                mapbox_style="carto-darkmatter", # Estilo elegante e "inteligencia"
                title="Distribución Geográfica del Delito en la Región Puno"
            )
            fig_mapa.update_layout(margin={"r":0,"t":40,"l":0,"b":0})
            st.plotly_chart(fig_mapa, use_container_width=True)
            
            st.info("💡 **Nota Novedosa:** Las burbujas (hotspots) indican la intensidad criminal. Un mayor tamaño y un color más rojo (como en San Román) señalan focos prioritarios para políticas de seguridad.")
        else:
            st.warning("No se encontraron provincias de Puno en los datos para graficar el mapa.")

    else:
        st.warning("El archivo no tiene una columna llamada 'PROV_HECHO' para agrupar los datos.")

except Exception as e:
    st.error(f"🚨 Ocurrió un error en el sistema: {e}")