import streamlit as st
import plotly.graph_objects as go
import pandas as pd
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

    # NOMBRES EXACTOS DE TUS COLUMNAS
    COL_CORREO = "Tu Correo Electrónico"
    COL_EVALUADO = "Nombre de la persona Evaluada"
    COL_RELACION = "Tu relación con el evaluado"
    
    COL_FORTALEZAS = "¿Cuáles son las mayores fortalezas de esta persona?"
    COL_OPORTUNIDADES = "¿Cuáles son sus principales oportunidades de desarrollo?"
    COL_SOBREUTILIZADA = "¿Hay alguna fortaleza que esta persona esté sobreutilizando?"

    tab1, tab2 = st.tabs(["👤 Mi Reporte Individual", "📊 Dashboard CEO"])

    with tab1:
        st.header("Consulta de Resultados Individuales")
        st.write("Introduce tu correo electrónico para acceder a tus resultados.")
        
        # CUADRO DE TEXTO PARA EL CORREO
        email_input = st.text_input("Correo electrónico:", placeholder="ejemplo@loguerkim.mx").strip()
        btn_validar = st.button("Validar y Entrar")

        if btn_validar and email_input:
            # BUSQUEDA: Filtramos donde el correo coincida (ignorando mayúsculas/minúsculas)
            # Y donde la relación sea 'Self' para asegurar que es SU reporte
            df_usuario = df[
                (df[COL_CORREO].astype(str).str.lower() == email_input.lower()) & 
                (df[COL_RELACION].astype(str).str.strip().str.lower() == 'self')
            ]
            
            if not df_usuario.empty:
                nombre_usuario = df_usuario[COL_EVALUADO].iloc[0]
                st.success(f"✅ Acceso concedido: {nombre_usuario}")
                st.divider()
                
                # Ejecutar motor de cálculo para este usuario
                res = process_hogan_logic(df, nombre_usuario, MAPEO_HOGAN, MIN_OBS)
                
                # Visualización: Gráfica
                fig = go.Figure()
                fig.add_trace(go.Bar(x=res['Categoría'], y=res['Autoevaluación (Self)'], name='Autoevaluación (Self)', marker_color='#1E40AF'))
                fig.add_trace(go.Bar(x=res['Categoría'], y=res['Evaluaciones Recibidas (Others)'], name='Promedio Otros (Others)', marker_color='#F59E0B'))
                fig.update_layout(yaxis_range=[1,7], barmode='group', legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1))
                st.plotly_chart(fig, use_container_width=True)
                
                # Tabla de datos
                st.subheader("Resultados por categoría")
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
                st.error("No se encontró ninguna autoevaluación (Self) vinculada a este correo. Por favor, verifica que el correo sea el mismo que registraste.")

    with tab2:
        # Pestaña CEO (Mantiene la lógica de contraseña)
        st.header("Dashboard Administrativo")
        if 'ceo_auth' not in st.session_state: st.session_state['ceo_auth'] = False

        if not st.session_state['ceo_auth']:
            pw = st.text_input("Contraseña CEO:", type="password")
            if st.button("Acceder"):
                if pw == PASSWORD_CEO:
                    st.session_state['ceo_auth'] = True
                    st.rerun()
                else: st.error("Contraseña incorrecta")
        
        if st.session_state['ceo_auth']:
            st.subheader("📌 Promedio Global Organizacional")
            glob = get_global_metrics(df, MAPEO_HOGAN, MIN_OBS)
            st.table(glob)
            
            st.divider()
            lideres = sorted(df[COL_EVALUADO].unique().tolist())
            lider_sel = st.selectbox("Auditar Líder Específico:", lideres)
            
            if lider_sel:
                res_lider = process_hogan_logic(df, lider_sel, MAPEO_HOGAN, MIN_OBS)
                st.dataframe(
                    res_lider.style.format({
                        "Cobertura": "{:.0%}", 
                        "Autoevaluación (Self)": "{:.2f}", 
                        "Evaluaciones Recibidas (Others)": "{:.2f}"
                    }), 
                    hide_index=True, use_container_width=True
                )
                
                st.subheader("💬 Feedback Cualitativo")
                fb_df = df[df[COL_EVALUADO] == lider_sel][[COL_FORTALEZAS, COL_OPORTUNIDADES, COL_SOBREUTILIZADA]]
                st.dataframe(fb_df.dropna(how='all'), use_container_width=True)
                
                render_glosario()

if __name__ == "__main__":
    main()
