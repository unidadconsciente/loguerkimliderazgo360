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
        
        for term, desc in GLOSARIO.items():
            if term not in ["Calidad", "Cobertura"]:
                st.write(f"**{term}:** {desc}")

def main():
    st.set_page_config(page_title="Hogan 360 - Loguerkim", layout="wide")
    
    # Encabezado
    col_logo, col_titulo = st.columns([1, 3])
    with col_logo:
        try: st.image("logologuerkim.PNG", width=250)
        except: st.warning("Logo no encontrado")
    with col_titulo:
        st.markdown("<h1 style='padding-top: 20px;'>Resultados de encuesta 360 Loguerkim</h1>", unsafe_allow_html=True)
    st.divider()

    try:
        df = get_drive_data()
    except Exception as e:
        st.error(f"Error de conexión: {e}"); return

    COL_CORREO = "Tu Correo Electrónico"
    COL_NOMBRE_EVALUADOR = "Tu Nombre (Evaluador)"
    COL_EVALUADO = "Nombre de la persona Evaluada"
    
    tab1, tab2 = st.tabs(["👤 Mi Reporte Individual", "📊 Dashboard CEO"])

    with tab1:
        st.header("Consulta de Resultados Individuales")
        email_input = st.text_input("Introduce tu correo electrónico:").strip().lower()
        if st.button("Generar Reporte") and email_input:
            user_data = df[df[COL_CORREO].astype(str).str.strip().str.lower() == email_input]
            if not user_data.empty:
                nombre_usuario = str(user_data[COL_NOMBRE_EVALUADOR].iloc[0]).strip()
                st.success(f"✅ Bienvenido {nombre_usuario}, este es tu reporte")
                res = process_hogan_logic(df, nombre_usuario, MAPEO_HOGAN)
                
                fig = go.Figure()
                fig.add_trace(go.Bar(x=res['Categoría'], y=res['Autoevaluación'], name='Mi Autoevaluación', marker_color='#1E40AF'))
                fig.add_trace(go.Bar(x=res['Categoría'], y=res['Superior'], name='Jefes (Superior)', marker_color='#F59E0B'))
                fig.add_trace(go.Bar(x=res['Categoría'], y=res['Par'], name='Pares (Colegas)', marker_color='#10B981'))
                fig.add_trace(go.Bar(x=res['Categoría'], y=res['Subordinado'], name='Reportes (Subordinados)', marker_color='#8B5CF6'))
                fig.update_layout(yaxis_range=[1,7], barmode='group', legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1))
                st.plotly_chart(fig, use_container_width=True)
                
                st.dataframe(res.style.format({"Cobertura": "{:.0%}", "Autoevaluación": "{:.2f}", "Superior": "{:.2f}", "Par": "{:.2f}", "Subordinado": "{:.2f}"}), hide_index=True, use_container_width=True)
                render_glosario()
            else:
                st.error("Correo no encontrado.")

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
            
            fig_glob = go.Figure()
            colors = {'Autoevaluación': '#1E40AF', 'Superior': '#F59E0B', 'Par': '#10B981', 'Subordinado': '#8B5CF6'}
            for col, color in colors.items():
                fig_glob.add_trace(go.Bar(x=glob['Categoría'], y=glob[col], name=col, marker_color=color))
            fig_glob.update_layout(yaxis_range=[1,7], barmode='group', legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1))
            st.plotly_chart(fig_glob, use_container_width=True)
            st.table(glob)

            st.divider()

            # --- BLOQUE RESTAURADO: AUDITORÍA POR LÍDER ---
            st.subheader("🔍 Auditoría por Líder")
            lideres = sorted([l for l in df[COL_EVALUADO].unique() if str(l).strip()])
            lider_sel = st.selectbox("Selecciona un líder para auditar:", lideres)
            
            if lider_sel:
                res_l = process_hogan_logic(df, lider_sel, MAPEO_HOGAN)
                fig_l = go.Figure()
                for col, color in colors.items():
                    fig_l.add_trace(go.Bar(x=res_l['Categoría'], y=res_l[col], name=col, marker_color=color))
                fig_l.update_layout(title=f"Resultados: {lider_sel}", yaxis_range=[1,7], barmode='group', legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1))
                st.plotly_chart(fig_l, use_container_width=True)
                st.dataframe(res_l, hide_index=True, use_container_width=True)

if __name__ == "__main__":
    main()
