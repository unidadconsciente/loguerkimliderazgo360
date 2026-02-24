import streamlit as st
import plotly.graph_objects as go
import pandas as pd
from sheet_acces import get_drive_data, get_accesos_data
from calculos import process_hogan_logic, get_global_metrics, get_anonymous_feedback
from import_data import PASSWORD_CEO, GLOSARIO, MAPEO_HOGAN, MIN_OBS
from sync_accesos import sync_users

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
    col_l, col_t = st.columns([1, 3])
    with col_l:
        try: st.image("logologuerkim.PNG", width=250)
        except: st.warning("Logo no encontrado")
    with col_t:
        st.markdown("<h1 style='padding-top: 20px;'>Resultados de encuesta 360 Loguerkim</h1>", unsafe_allow_html=True)
    st.divider()

    try:
        df = get_drive_data()
        df_accesos = get_accesos_data()
    except Exception as e:
        st.error(f"Error de conexión: {e}"); return

    COL_CORREO = "Tu Correo Electrónico"
    COL_NOMBRE_EVALUADOR = "Tu Nombre (Evaluador)"
    COL_EVALUADO = "Nombre de la persona Evaluada"
    
    tab1, tab2 = st.tabs(["👤 Mi Reporte Individual", "📊 Dashboard CEO"])

    with tab1:
        if "user_auth" not in st.session_state:
            st.session_state["user_auth"] = False
            st.session_state["user_email"] = ""

        if not st.session_state["user_auth"]:
            st.header("Consulta de Resultados")
            c1, c2 = st.columns(2)
            with c1: email_in = st.text_input("Introduce tu correo electrónico:").strip().lower()
            with c2: pass_in = st.text_input("Introduce tu contraseña:", type="password").strip()
            
            if st.button("Generar Reporte"):
                # Doble Validación solicitada
                en_base = email_in in df[COL_CORREO].astype(str).str.lower().values
                match_acc = df_accesos[(df_accesos['Correo'].astype(str).str.lower() == email_in) & (df_accesos['Contraseña'].astype(str) == pass_in)]
                
                if en_base and not match_acc.empty:
                    st.session_state["user_auth"] = True
                    st.session_state["user_email"] = email_in
                    st.rerun()
                elif not en_base:
                    st.error("Este correo no tiene registros en la base de respuestas.")
                else:
                    st.error("Contraseña incorrecta.")

        if st.session_state["user_auth"]:
            email = st.session_state["user_email"]
            nombre = str(df[df[COL_CORREO].astype(str).str.lower() == email][COL_NOMBRE_EVALUADOR].iloc[0]).strip()
            
            c_welcome, c_logout = st.columns([4,1])
            with c_welcome: st.success(f"✅ Bienvenido {nombre}, este es tu reporte")
            with c_logout:
                if st.button("Cerrar Sesión"):
                    st.session_state["user_auth"] = False
                    st.rerun()

            res = process_hogan_logic(df, nombre, MAPEO_HOGAN)
            
            # Gráfica
            fig = go.Figure()
            fig.add_trace(go.Bar(x=res['Categoría'], y=res['Autoevaluación'], name='Mi Autoevaluación', marker_color='#1E40AF'))
            fig.add_trace(go.Bar(x=res['Categoría'], y=res['Superior'], name='Jefes (Superior)', marker_color='#F59E0B'))
            fig.add_trace(go.Bar(x=res['Categoría'], y=res['Par'], name='Pares (Colegas)', marker_color='#10B981'))
            fig.add_trace(go.Bar(x=res['Categoría'], y=res['Subordinado'], name='Reportes (Subordinados)', marker_color='#8B5CF6'))
            fig.update_layout(yaxis_range=[1,7], barmode='group', legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1))
            st.plotly_chart(fig, use_container_width=True)
            
            # Tabla formateada
            st.dataframe(res.style.format({"Cobertura": "{:.0%}", "Autoevaluación": "{:.2f}", "Superior": "{:.2f}", "Par": "{:.2f}", "Subordinado": "{:.2f}"}), hide_index=True, use_container_width=True)
            
            st.divider()
            st.subheader("🗣️ Comentarios Cualitativos Anónimos")
            st.dataframe(get_anonymous_feedback(df, nombre), use_container_width=True, hide_index=True)
            render_glosario()

    with tab2:
        st.header("Dashboard Administrativo")
        if not st.session_state.get('ceo_auth', False):
            pw = st.text_input("Contraseña CEO:", type="password")
            if st.button("Acceder Dashboard"):
                if pw == PASSWORD_CEO:
                    st.session_state['ceo_auth'] = True
                    st.rerun()
                else: st.error("Acceso denegado")
        else:
            # BOTÓN SYNC DENTRO DEL DASHBOARD
            if st.button("🔄 Sincronizar Usuarios con Drive"):
                with st.spinner("Actualizando pestaña de Accesos..."):
                    msj = sync_users()
                    st.cache_data.clear() # Limpia caché para leer lo recién escrito
                    st.info(msj)

            st.divider()
            st.subheader("📌 Benchmark Organizacional (Promedio Global)")
            glob = get_global_metrics(df, MAPEO_HOGAN)
            st.table(glob)

            st.subheader("Auditoría por Líder")
            lider_sel = st.selectbox("Líder:", sorted(df[COL_EVALUADO].unique()))
            if lider_sel:
                st.dataframe(process_hogan_logic(df, lider_sel, MAPEO_HOGAN), use_container_width=True, hide_index=True)
                st.subheader(f"Comentarios para {lider_sel}")
                st.dataframe(get_anonymous_feedback(df, lider_sel), use_container_width=True, hide_index=True)
            
            # REQUERIMIENTO: Glosario al final del Dashboard
            render_glosario()

if __name__ == "__main__":
    main()
