import streamlit as st
import plotly.graph_objects as go
import pandas as pd

# Importación de tus otros módulos
from sheet_acces import get_drive_data
from calculos import process_hogan_logic, get_global_metrics
from import_data import PASSWORD_CEO, GLOSARIO, MAPEO_HOGAN, MIN_OBS

def render_glosario():
    """Muestra el glosario de términos al final de los reportes."""
    st.markdown("---")
    with st.expander("🔎 Glosario de términos y Metodología"):
        for term, desc in GLOSARIO.items():
            st.write(f"**{term}:** {desc}")

def main():
    st.set_page_config(page_title="Hogan 360 - Loguerkim", layout="wide")
    
    # Carga de datos inicial
    try:
        df = get_drive_data()
    except Exception as e:
        st.error(f"Fallo en la conexión con la base de datos: {e}")
        return

    # Definición de columnas por posición para evitar errores de nombres
    # Basado en tu estructura: Col 3 (Correo), Col 4 (Evaluado), Col 6 (Relación)
    COL_CORREO = df.columns[3]
    COL_EVALUADO = df.columns[4]
    COL_RELACION = df.columns[6]

    tab1, tab2 = st.tabs(["👤 Mi Reporte Individual", "📊 Dashboard CEO"])

    # ---------------------------------------------------------
    # PESTAÑA 1: REPORTE INDIVIDUAL
    # ---------------------------------------------------------
    with tab1:
        st.header("Consulta de Resultados Individuales")
        st.info("Escribe tu correo para validar tu identidad y ver tu reporte personalizado.")
        
        email_input = st.text_input("Ingresa tu correo corporativo:", placeholder="ejemplo@loguerkim.mx").strip().lower()
        btn_validar = st.button("Validar Correo")

        if btn_validar and email_input:
            # Lógica de Identificación: Buscamos la fila donde el correo sea SELF
            # Normalizamos para que coincida sin importar mayúsculas o espacios
            identidad = df[
                (df[COL_CORREO].astype(str).str.strip().str.lower() == email_input) & 
                (df[COL_RELACION].astype(str).str.strip().str.lower() == 'self')
            ]
            
            if not identidad.empty:
                nombre_usuario = identidad[COL_EVALUADO].iloc[0]
                st.success(f"✅ Identidad validada: Bienvenido, {nombre_usuario}")
                st.divider()
                
                st.subheader(f"📊 Resultados de Liderazgo para: {nombre_usuario}")
                
                # Procesamiento de datos (Motor de cálculo)
                res = process_hogan_logic(df, nombre_usuario, MAPEO_HOGAN, MIN_OBS)
                
                # --- Visualización Gráfica ---
                fig = go.Figure()
                fig.add_trace(go.Bar(
                    x=res['Categoría'], 
                    y=res['Autoevaluación (Self)'], 
                    name='Autoevaluación (Self)', 
                    marker_color='#1E40AF'
                ))
                fig.add_trace(go.Bar(
                    x=res['Categoría'], 
                    y=res['Evaluaciones Recibidas (Others)'], 
                    name='Evaluaciones Recibidas (Others)', 
                    marker_color='#F59E0B'
                ))
                fig.update_layout(
                    yaxis_range=[1,7], 
                    barmode='group',
                    legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
                )
                st.plotly_chart(fig, use_container_width=True)
                
                # --- Tabla de Resultados ---
                st.subheader("📋 Resultados por categoría")
                st.dataframe(
                    res.style.format({
                        "Cobertura": "{:.0%}",
                        "Autoevaluación (Self)": "{:.2f}",
                        "Evaluaciones Recibidas (Others)": "{:.2f}",
                        "Brecha (Gap)": "{:.2f}"
                    }), 
                    hide_index=True,
                    use_container_width=True
                )
                
                render_glosario()
            else:
                st.error("❌ No se encontró una autoevaluación (Self) vinculada a este correo. Asegúrate de que es el mismo correo que usaste en el formulario.")

    # ---------------------------------------------------------
    # PESTAÑA 2: DASHBOARD CEO
    # ---------------------------------------------------------
    with tab2:
        st.header("Dashboard Administrativo")
        
        # Control de Acceso
        if 'ceo_auth' not in st.session_state:
            st.session_state['ceo_auth'] = False

        col_pw1, col_pw2 = st.columns([3, 1])
        with col_pw1:
            pw = st.text_input("Contraseña de acceso:", type="password")
        with col_pw2:
            st.write(" ") # Espaciador
            if st.button("Acceder"):
                if pw == PASSWORD_CEO:
                    st.session_state['ceo_auth'] = True
                    st.rerun()
                else:
                    st.error("Clave incorrecta")

        # Contenido Protegido
        if st.session_state['ceo_auth']:
            st.success("Acceso autorizado como CEO")
            
            # --- SECCIÓN A: MÉTRICAS GLOBALES ---
            st.divider()
            st.subheader("📌 Benchmark Organizacional (Promedio Global)")
            st.write("Este es el promedio de todos los líderes evaluados en la organización.")
            
            glob = get_global_metrics(df, MAPEO_HOGAN, MIN_OBS)
            st.table(glob)
            
            # --- SECCIÓN B: AUDITORÍA INDIVIDUAL ---
            st.divider()
            st.subheader("🔍 Detalle Individual por Líder")
            
            nombres_lideres = sorted(df[COL_EVALUADO].unique())
            lider_sel = st.selectbox("Selecciona un Líder para ver su detalle:", nombres_lideres)
            
            if lider_sel:
                res_lider = process_hogan_logic(df, lider_sel, MAPEO_HOGAN, MIN_OBS)
                
                st.write(f"Viendo resultados de: **{lider_sel}**")
                st.dataframe(
                    res_lider.style.format({
                        "Cobertura": "{:.0%}",
                        "Autoevaluación (Self)": "{:.2f}",
                        "Evaluaciones Recibidas (Others)": "{:.2f}",
                        "Brecha (Gap)": "{:.2f}"
                    }), 
                    hide_index=True,
                    use_container_width=True
                )
                
                # --- SECCIÓN C: FEEDBACK CUALITATIVO ---
                st.subheader("💬 Feedback Cualitativo")
                # Tomamos las últimas 3 columnas (Fortalezas, Oportunidades, Sobreutilización)
                feedback = df[df[COL_EVALUADO] == lider_sel].iloc[:, -3:]
                # Renombramos para claridad
                feedback.columns = ["Mayores Fortalezas", "Oportunidades de Desarrollo", "Fortalezas Sobreutilizadas"]
                st.dataframe(feedback.dropna(how='all'), use_container_width=True)
                
                render_glosario()

if __name__ == "__main__":
    main()
