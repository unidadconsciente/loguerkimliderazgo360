import streamlit as st
import plotly.graph_objects as go
import pandas as pd
from sheet_acces import get_drive_data
from calculos import process_hogan_logic, get_global_metrics
from import_data import PASSWORD_CEO, GLOSARIO, MAPEO_HOGAN, MIN_OBS

def render_glosario():
    st.markdown("---")
    with st.expander("🔎 Glosario de términos y Metodología"):
        st.write("### 📊 Indicadores de Validez")
        st.write("**Cobertura:** Muestra qué tanto feedback recibiste en cada área. Es el porcentaje de conductas (preguntas) de esa categoría que tus evaluadores sí contestaron.")
        st.write("**Calidad:** Nivel de representatividad estadística basada en la cobertura.")
        st.write("- 🟢 **Sólido (>80%):** Feedback completo. Datos seguros.")
        st.write("- 🟡 **Cautela (50-80%):** Faltan respuestas; usar como guía parcial.")
        st.write("- 🔴 **Insuficiente (<50%):** Base débil; promedios posiblemente sesgados.")
        st.markdown("---")
        

def main():
    # 1. Configuración de página (SIEMPRE PRIMERO)
    st.set_page_config(page_title="Hogan 360 - Loguerkim", layout="wide")
    
    # 2. Encabezado con Logo y Título
    col_logo, col_titulo = st.columns([1, 3])
    
    with col_logo:
        try:
            # Actualizado al nombre exacto de tu archivo
            st.image("logologuerkim.PNG", width=280)
        except:
            st.warning("⚠️ logologuerkim.PNG no encontrado")

    with col_titulo:
        st.markdown("<h1 style='padding-top: 20px;'>Resultados de encuesta 360 Loguerkim</h1>", unsafe_allow_html=True)

    st.divider()

    try:
        df = get_drive_data()
    except Exception as e:
        st.error(f"Error de conexión: {e}")
        return

    # NOMBRES LITERALES DE COLUMNAS
    COL_CORREO = "Tu Correo Electrónico"
    COL_NOMBRE_EVALUADOR = "Tu Nombre (Evaluador)"
    COL_EVALUADO = "Nombre de la persona Evaluada"
    COL_RELACION = "Tu relación con el evaluado"
    
    COL_FORTALEZAS = "¿Cuáles son las mayores fortalezas de esta persona?"
    COL_OPORTUNIDADES = "¿Cuáles son sus principales oportunidades de desarrollo?"
    COL_SOBREUTILIZADA = "¿Hay alguna fortaleza que esta persona esté sobreutilizando?"

    tab1, tab2 = st.tabs(["👤 Mi Reporte Individual", "📊 Dashboard CEO"])

    # --- PESTAÑA 1: REPORTE INDIVIDUAL ---
    with tab1:
        st.header("Consulta de Resultados Individuales")
        email_input = st.text_input("Introduce tu correo electrónico:").strip().lower()
        
        if st.button("Generar Reporte") and email_input:
            user_data = df[df[COL_CORREO].astype(str).str.strip().str.lower() == email_input]
            
            if not user_data.empty:
                nombre_usuario = str(user_data[COL_NOMBRE_EVALUADOR].iloc[0]).strip()
                st.success(f"✅ Bienvenido {nombre_usuario}, este es tu reporte")
                st.divider()
                
                # Motor de cálculo
                res = process_hogan_logic(df, nombre_usuario, MAPEO_HOGAN)
                
                # Gráfica Plotly
                fig = go.Figure()
                fig.add_trace(go.Bar(x=res['Categoría'], y=res['Autoevaluación'], name='Mi Autoevaluación', marker_color='#1E40AF'))
                fig.add_trace(go.Bar(x=res['Categoría'], y=res['Evaluación de los demás'], name='Evaluación de los demás', marker_color='#F59E0B'))
                fig.update_layout(yaxis_range=[1,7], barmode='group', legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1))
                st.plotly_chart(fig, use_container_width=True)
                
                # Tabla de resultados
                st.subheader("Desglose de puntuaciones")
                res_clean = res.copy()
                for col in ["Autoevaluación", "Evaluación de los demás", "Brecha (Gap)"]:
                    res_clean[col] = pd.to_numeric(res_clean[col], errors='coerce').fillna(0.0)

                st.dataframe(
                    res_clean.style.format({
                        "Cobertura": "{:.0%}", 
                        "Autoevaluación": "{:.2f}", 
                        "Evaluación de los demás": "{:.2f}", 
                        "Brecha (Gap)": "{:.2f}"
                    }), 
                    hide_index=True, 
                    use_container_width=True
                )
                
                # Feedback cualitativo
                st.subheader("💬 Feedback de mis evaluadores")
                fb_df = df[df[COL_EVALUADO].astype(str).str.strip() == nombre_usuario][[COL_FORTALEZAS, COL_OPORTUNIDADES, COL_SOBREUTILIZADA]]
                st.dataframe(fb_df.dropna(how='all'), use_container_width=True)
                
                render_glosario()
            else:
                st.error("Correo no encontrado en la base de datos.")

    # --- PESTAÑA 2: DASHBOARD CEO ---
    with tab2:
        st.header("Dashboard Administrativo")
        if 'ceo_auth' not in st.session_state: st.session_state['ceo_auth'] = False
        
        if not st.session_state['ceo_auth']:
            pw = st.text_input("Contraseña CEO:", type="password")
            if st.button("Acceder"):
                if pw == PASSWORD_CEO:
                    st.session_state['ceo_auth'] = True
                    st.rerun()
                else: st.error("Acceso denegado")
        
        if st.session_state['ceo_auth']:
            st.subheader("📌 Benchmark Organizacional (Promedio Global)")
            glob = get_global_metrics(df, MAPEO_HOGAN)
            
            # Gráfica Global
            fig_glob = go.Figure()
            fig_glob.add_trace(go.Bar(x=glob['Categoría'], y=glob['Autoevaluación'], name='Autoevaluación (Global)', marker_color='#1E40AF'))
            fig_glob.add_trace(go.Bar(x=glob['Categoría'], y=glob['Evaluación de los demás'], name='Evaluación de los demás (Global)', marker_color='#F59E0B'))
            fig_glob.update_layout(yaxis_range=[1,7], barmode='group', legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1))
            st.plotly_chart(fig_glob, use_container_width=True)
            
            st.table(glob)
            st.divider()
            
            # Auditoría
            st.subheader("🔍 Auditoría por Líder")
            lideres = sorted([l for l in df[COL_EVALUADO].unique() if str(l).strip()])
            lider_sel = st.selectbox("Selecciona un líder para auditar:", lideres)
            
            if lider_sel:
                res_l = process_hogan_logic(df, lider_sel, MAPEO_HOGAN)
                fig_l = go.Figure()
                fig_l.add_trace(go.Bar(x=res_l['Categoría'], y=res_l['Autoevaluación'], name='Autoevaluación', marker_color='#1E40AF'))
                fig_l.add_trace(go.Bar(x=res_l['Categoría'], y=res_l['Evaluación de los demás'], name='Evaluación de los demás', marker_color='#F59E0B'))
                fig_l.update_layout(title=f"Resultados: {lider_sel}", yaxis_range=[1,7], barmode='group', legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1))
                st.plotly_chart(fig_l, use_container_width=True)
                st.dataframe(res_l, hide_index=True, use_container_width=True)

if __name__ == "__main__":
    main()
