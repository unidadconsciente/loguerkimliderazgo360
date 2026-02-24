import streamlit as st
import plotly.graph_objects as go
import pandas as pd
from sheet_acces import get_drive_data, get_accesos_data
from calculos import process_hogan_logic, get_global_metrics, get_anonymous_feedback
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
    
    col_logo, col_titulo = st.columns([1, 3])
    with col_logo:
        try: st.image("logologuerkim.PNG", width=250)
        except: st.warning("Logo no encontrado")
    with col_titulo:
        st.markdown("<h1 style='padding-top: 20px;'>Resultados de encuesta 360 Loguerkim</h1>", unsafe_allow_html=True)
    st.divider()

    try:
        df = get_drive_data()
        df_accesos = get_accesos_data()
    except Exception as e:
        st.error(f"Error de conexión: {e}")
        return

    COL_CORREO = "Tu Correo Electrónico"
    COL_NOMBRE_EVALUADOR = "Tu Nombre (Evaluador)"
    COL_EVALUADO = "Nombre de la persona Evaluada"
    
    tab1, tab2 = st.tabs(["👤 Mi Reporte Individual", "📊 Dashboard CEO"])

    with tab1:
        st.header("Consulta de Resultados Individuales")
        
        if "user_auth" not in st.session_state:
            st.session_state["user_auth"] = False
            st.session_state["user_email"] = ""

        if not st.session_state["user_auth"]:
            col1, col2 = st.columns(2)
            with col1:
                email_input = st.text_input("Introduce tu correo electrónico:").strip().lower()
            with col2:
                pass_input = st.text_input("Introduce tu contraseña:", type="password").strip()

            # UX Restaurado: Generar Reporte
            if st.button("Generar Reporte"):
                if email_input and pass_input:
                    # VALIDACIÓN DE ACCESO SOLICITADA
                    en_base = email_input in df[COL_CORREO].astype(str).str.lower().values
                    match_acc = df_accesos[
                        (df_accesos['Correo'].astype(str).str.lower() == email_input) & 
                        (df_accesos['Contraseña'].astype(str) == pass_input)
                    ]
                    
                    if en_base and not match_acc.empty:
                        st.session_state["user_auth"] = True
                        st.session_state["user_email"] = email_input
                        st.rerun()
                    elif not en_base:
                        st.error("Este correo no está registrado en la base de datos de respuestas.")
                    else:
                        st.error("Contraseña incorrecta.")
                else:
                    st.warning("Por favor, ingresa correo y contraseña.")

        if st.session_state["user_auth"]:
            email = st.session_state["user_email"]
            user_row = df[df[COL_CORREO].astype(str).str.lower() == email]
            nombre = str(user_row[COL_NOMBRE_EVALUADOR].iloc[0]).strip()
            
            c_nom, c_logout = st.columns([4,1])
            with c_nom:
                st.success(f"✅ Bienvenido {nombre}, este es tu reporte")
            with c_logout:
                if st.button("Cerrar Sesión"):
                    st.session_state["user_auth"] = False
                    st.rerun()

            res = process_hogan_logic(df, nombre, MAPEO_HOGAN)
            
            # Gráficas Restauradas (Traza por traza)
            fig = go.Figure()
            fig.add_trace(go.Bar(x=res['Categoría'], y=res['Autoevaluación'], name='Mi Autoevaluación', marker_color='#1E40AF'))
            fig.add_trace(go.Bar(x=res['Categoría'], y=res['Superior'], name='Jefes (Superior)', marker_color='#F59E0B'))
            fig.add_trace(go.Bar(x=res['Categoría'], y=res['Par'], name='Pares (Colegas)', marker_color='#10B981'))
            fig.add_trace(go.Bar(x=res['Categoría'], y=res['Subordinado'], name='Reportes (Subordinados)', marker_color='#8B5CF6'))
            
            fig.update_layout(
                yaxis_range=[1,7], 
                barmode='group', 
                legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
            )
            st.plotly_chart(fig, use_container_width=True)
            
            # Formateo Numérico Restaurado
            st.dataframe(
                res.style.format({
                    "Cobertura": "{:.0%}", 
                    "Autoevaluación": "{:.2f}", 
                    "Superior": "{:.2f}", 
                    "Par": "{:.2f}", 
                    "Subordinado": "{:.2f}"
                }), 
                hide_index=True, 
                use_container_width=True
            )
            
            st.divider()
            st.subheader("🗣️ Comentarios Cualitativos Anónimos")
            st.dataframe(get_anonymous_feedback(df, nombre), use_container_width=True, hide_index=True)
            render_glosario()

    with tab2:
        st.header("Dashboard Administrativo")
        if 'ceo_auth' not in st.session_state: st.session_state['ceo_auth'] = False
        if not st.session_state['ceo_auth']:
            pw = st.text_input("Contraseña CEO:", type="password")
            if st.button("Acceder Dashboard"):
                if pw == PASSWORD_CEO:
                    st.session_state['ceo_auth'] = True
                    st.rerun()
                else: st.error("Acceso denegado")
        
        if st.session_state['ceo_auth']:
            # Función Nueva: Sincronización
            if st.button("🔄 Sincronizar Nuevos Usuarios"):
                from sync_accesos import sync_users
                sync_users()
            
            st.divider()
            st.subheader("📌 Benchmark Organizacional (Promedio Global)")
            glob = get_global_metrics(df, MAPEO_HOGAN)
            
            fig_glob = go.Figure()
            fig_glob.add_trace(go.Bar(x=glob['Categoría'], y=glob['Autoevaluación'], name='Autoevaluación', marker_color='#1E40AF'))
            fig_glob.add_trace(go.Bar(x=glob['Categoría'], y=glob['Superior'], name='Superior', marker_color='#F59E0B'))
            fig_glob.add_trace(go.Bar(x=glob['Categoría'], y=glob['Par'], name='Par', marker_color='#10B981'))
            fig_glob.add_trace(go.Bar(x=glob['Categoría'], y=glob['Subordinado'], name='Subordinado', marker_color='#8B5CF6'))
            fig_glob.update_layout(yaxis_range=[1,7], barmode='group', legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1))
            st.plotly_chart(fig_glob, use_container_width=True)
            
            st.table(glob)

            st.divider()
            st.subheader("🔍 Auditoría por Líder")
            lideres = sorted([l for l in df[COL_EVALUADO].unique() if str(l).strip()])
            lider_sel = st.selectbox("Selecciona un líder para auditar:", lideres)
            
            if lider_sel:
                res_l = process_hogan_logic(df, lider_sel, MAPEO_HOGAN)
                st.dataframe(res_l, use_container_width=True, hide_index=True)
                st.subheader(f"Comentarios para {lider_sel}")
                st.dataframe(get_anonymous_feedback(df, lider_sel), use_container_width=True, hide_index=True)

if __name__ == "__main__":
    main()
