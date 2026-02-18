import streamlit as st
import plotly.graph_objects as go
import pandas as pd

# Importación de tus otros módulos
from sheet_acces import get_drive_data
from calculos import process_hogan_logic, get_global_metrics
from import_data import PASSWORD_CEO, GLOSARIO, MAPEO_HOGAN, MIN_OBS

def render_glosario():
    st.markdown("---")
    with st.expander("🔎 Glosario de términos y Metodología"):
        for term, desc in GLOSARIO.items():
            st.write(f"**{term}:** {desc}")

def main():
    st.set_page_config(page_title="Hogan 360 - Loguerkim", layout="wide")
    
    try:
        df = get_drive_data()
    except Exception as e:
        st.error(f"Fallo en la conexión: {e}")
        return

    # Definición de columnas por posición
    COL_CORREO = df.columns[3]
    COL_EVALUADO = df.columns[4]
    COL_RELACION = df.columns[6]

    tab1, tab2 = st.tabs(["👤 Mi Reporte Individual", "📊 Dashboard CEO"])

    # ---------------------------------------------------------
    # PESTAÑA 1: REPORTE INDIVIDUAL (CON SELECTOR ÚNICO)
    # ---------------------------------------------------------
    with tab1:
        st.header("Consulta de Resultados Individuales")
        
        # Filtramos la base para mostrar SOLO correos que tienen autoevaluación (Self)
        # Esto garantiza que si el correo aparece en la lista, el reporte EXISTE.
        filtro_self = df[df[COL_RELACION].astype(str).str.strip().str.lower() == 'self']
        lista_correos = sorted(filtro_self[COL_CORREO].unique())

        st.info("Selecciona tu correo de la lista para acceder a tus resultados.")
        
        # Cambio de text_input a selectbox
        email_seleccionado = st.selectbox(
            "Selecciona tu correo corporativo:", 
            options=["-- Selecciona uno --"] + lista_correos
        )
        
        btn_validar = st.button("Generar Reporte")

        if btn_validar and email_seleccionado != "-- Selecciona uno --":
            # Buscamos la fila correspondiente a ese correo seleccionado
            identidad = filtro_self[filtro_self[COL_CORREO] == email_seleccionado]
            
            if not identidad.empty:
                nombre_usuario = identidad[COL_EVALUADO].iloc[0]
                st.success(f"✅ Bienvenido, {nombre_usuario}")
                st.divider()
                
                st.subheader(f"📊 Perfil de Liderazgo: {nombre_usuario}")
                
                # Motor de cálculo
                res = process_hogan_logic(df, nombre_usuario, MAPEO_HOGAN, MIN_OBS)
                
                # Gráfica
                fig = go.Figure()
                fig.add_trace(go.Bar(x=res['Categoría'], y=res['Autoevaluación (Self)'], name='Autoevaluación (Self)', marker_color='#1E40AF'))
                fig.add_trace(go.Bar(x=res['Categoría'], y=res['Evaluaciones Recibidas (Others)'], name='Evaluaciones Recibidas (Others)', marker_color='#F59E0B'))
                fig.update_layout(yaxis_range=[1,7], barmode='group')
                st.plotly_chart(fig, use_container_width=True)
                
                st.subheader("📋 Resultados por categoría")
                st.dataframe(
                    res.style.format({
                        "Cobertura": "{:.0%}",
                        "Autoevaluación (Self)": "{:.2f}",
                        "Evaluaciones Recibidas (Others)": "{:.2f}",
                        "Brecha (Gap)": "{:.2f}"
                    }), 
                    hide_index=True, use_container_width=True
                )
                render_glosario()
            else:
                st.error("Error al recuperar los datos del perfil.")

    # ---------------------------------------------------------
    # PESTAÑA 2: DASHBOARD CEO
    # ---------------------------------------------------------
    with tab2:
        st.header("Dashboard Administrativo")
        
        if 'ceo_auth' not in st.session_state:
            st.session_state['ceo_auth'] = False

        col_pw1, col_pw2 = st.columns([3, 1])
        with col_pw1:
            pw = st.text_input("Contraseña de acceso:", type="password")
        with col_pw2:
            st.write(" ") 
            if st.button("Acceder"):
                if pw == PASSWORD_CEO:
                    st.session_state['ceo_auth'] = True
                    st.rerun()
                else:
                    st.error("Clave incorrecta")

        if st.session_state['ceo_auth']:
            # SECCIÓN GLOBAL
            st.subheader("📌 Promedio Global Organizacional")
            glob = get_global_metrics(df, MAPEO_HOGAN, MIN_OBS)
            st.table(glob)
            
            st.divider()
            # SECCIÓN INDIVIDUAL
            st.subheader("🔍 Auditoría por Líder")
            nombres_lideres = sorted(df[COL_EVALUADO].unique())
            lider_sel = st.selectbox("Selecciona un Líder:", nombres_lideres)
            
            if lider_sel:
                res_lider = process_hogan_logic(df, lider_sel, MAPEO_HOGAN, MIN_OBS)
                st.dataframe(
                    res_lider.style.format({
                        "Cobertura": "{:.0%}",
                        "Autoevaluación (Self)": "{:.2f}",
                        "Evaluaciones Recibidas (Others)": "{:.2f}",
                        "Brecha (Gap)": "{:.2f}"
                    }), 
                    hide_index=True, use_container_width=True
                )
                
                st.subheader("💬 Feedback Cualitativo")
                feedback = df[df[COL_EVALUADO] == lider_sel].iloc[:, -3:]
                feedback.columns = ["Mayores Fortalezas", "Oportunidades de Desarrollo", "Fortalezas Sobreutilizadas"]
                st.dataframe(feedback.dropna(how='all'), use_container_width=True)
                render_glosario()

if __name__ == "__main__":
    main()
