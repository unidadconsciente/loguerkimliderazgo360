import streamlit as st
import plotly.graph_objects as go
import pandas as pd
from sheet_acces import get_drive_data
from calculos import process_hogan_logic, get_global_metrics
from import_data import PASSWORD_CEO, GLOSARIO

def render_glosario():
    with st.expander("🔎 Glosario de términos"):
        for term, desc in GLOSARIO.items():
            st.write(f"**{term}:** {desc}")

def main():
    st.set_page_config(page_title="Hogan 360", layout="wide")
    df = get_drive_data()

    tab1, tab2 = st.tabs(["👤 Mi Reporte Individual", "📊 Dashboard CEO"])

    with tab1:
        st.header("Consulta de Resultados Individuales")
        email = st.text_input("Ingresa tu correo corporativo:")
        btn_validar = st.button("Validar Correo")

        if btn_validar and email:
            # Lógica de identificación: Buscamos la fila donde el correo sea SELF
            identidad = df[(df['Tu Correo Electrónico'] == email) & (df['Tu relación con el evaluado'] == 'Self')]
            
            if not identidad.empty:
                nombre_usuario = identidad['Nombre de la persona Evaluada'].iloc[0]
                st.success(f"Bienvenido, {nombre_usuario}")
                st.subheader(f"Perfil de Liderazgo: {nombre_usuario}")
                
                res = process_hogan_logic(df, nombre_usuario)
                
                # Gráfica Plotly
                fig = go.Figure()
                fig.add_trace(go.Bar(x=res['Categoría'], y=res['Autoevaluación (Self)'], name='Autoevaluación', marker_color='#1E40AF'))
                fig.add_trace(go.Bar(x=res['Categoría'], y=res['Evaluaciones Recibidas (Others)'], name='Evaluaciones Recibidas', marker_color='#F59E0B'))
                fig.update_layout(yaxis_range=[1,7], barmode='group')
                st.plotly_chart(fig, use_container_width=True)
                
                st.subheader("Resultados por categoría")
                st.dataframe(res.style.format({"Cobertura": "{:.0%}"}), hide_index=True)
                render_glosario()
            else:
                st.error("No se encontró una autoevaluación vinculada a este correo.")

    with tab2:
        st.header("Acceso Administrativo")
        pw = st.text_input("Contraseña CEO:", type="password")
        btn_ceo = st.button("Acceder al Dashboard")

        if btn_ceo and pw == PASSWORD_CEO:
            st.session_state['ceo_auth'] = True

        if st.session_state.get('ceo_auth'):
            st.subheader("📌 Promedio Global Organizacional")
            glob = get_global_metrics(df)
            st.table(glob)
            
            st.divider()
            st.subheader("🔍 Auditoría Individual por Líder")
            lider_sel = st.selectbox("Selecciona al Líder:", df['Nombre de la persona Evaluada'].unique())
            
            if lider_sel:
                res_lider = process_hogan_logic(df, lider_sel)
                st.dataframe(res_lider.style.format({"Cobertura": "{:.0%}"}), hide_index=True)
                render_glosario()

if __name__ == "__main__":
    main()
