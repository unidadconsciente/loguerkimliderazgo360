import streamlit as st
import plotly.graph_objects as go
import pandas as pd

from sheet_acces import get_drive_data, get_accesos_data, get_participantes_data
from calculos import process_hogan_logic, get_global_metrics, get_anonymous_feedback
from import_data import PASSWORD_CEO, GLOSARIO, MAPEO_HOGAN
from sync_accesos import sync_users


COL_NOMBRE_EVALUADOR = "Tu Nombre (Evaluador)"
COL_CARGO_EVALUADOR = "Tu Cargo"
COL_EVALUADO = "Nombre de la persona Evaluada"
COL_CARGO_EVALUADO = "Cargo del Evaluado"


def _norm(value: str) -> str:
    return str(value).strip().lower()


def _icon(done: bool) -> str:
    return "✅" if done else "❌"


def _pair_key(nombre: str, cargo: str) -> str:
    return f"{_norm(nombre)}|||{_norm(cargo)}"


def _is_dg(cargo: str) -> bool:
    cargo_n = _norm(cargo)
    return cargo_n == "director general"


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


def build_valid_responses(df_resp: pd.DataFrame, df_part: pd.DataFrame) -> pd.DataFrame:
    if df_resp.empty or df_part.empty:
        return pd.DataFrame()

    participantes = df_part.copy()
    participantes["Nombre"] = participantes["Nombre"].astype(str).str.strip()
    participantes["Cargo"] = participantes["Cargo"].astype(str).str.strip()
    participantes["key"] = participantes.apply(
        lambda r: _pair_key(r["Nombre"], r["Cargo"]), axis=1
    )

    valid_keys = set(participantes["key"].tolist())

    df = df_resp.copy()
    df["evaluador_key"] = df.apply(
        lambda r: _pair_key(r.get(COL_NOMBRE_EVALUADOR, ""), r.get(COL_CARGO_EVALUADOR, "")),
        axis=1,
    )
    df["evaluado_key"] = df.apply(
        lambda r: _pair_key(r.get(COL_EVALUADO, ""), r.get(COL_CARGO_EVALUADO, "")),
        axis=1,
    )

    df = df[
        df["evaluador_key"].isin(valid_keys) &
        df["evaluado_key"].isin(valid_keys)
    ].copy()

    if "Timestamp" in df.columns:
        df["Timestamp"] = pd.to_datetime(df["Timestamp"], errors="coerce")
        df = df.sort_values("Timestamp").drop_duplicates(
            subset=["evaluador_key", "evaluado_key"],
            keep="last",
        )
    else:
        df = df.drop_duplicates(subset=["evaluador_key", "evaluado_key"], keep="last")

    return df


def build_tracking(df_resp: pd.DataFrame, df_part: pd.DataFrame):
    df_valid = build_valid_responses(df_resp, df_part)

    participantes = df_part.copy()
    participantes["Nombre"] = participantes["Nombre"].astype(str).str.strip()
    participantes["Cargo"] = participantes["Cargo"].astype(str).str.strip()
    participantes["key"] = participantes.apply(
        lambda r: _pair_key(r["Nombre"], r["Cargo"]), axis=1
    )

    dg_rows = participantes[participantes["Cargo"].astype(str).apply(_is_dg)]
    if dg_rows.empty:
        return pd.DataFrame(), {}

    dg = dg_rows.iloc[0]
    dg_key = dg["key"]

    done_pairs = set()
    if not df_valid.empty:
        done_pairs = set(
            df_valid.apply(
                lambda r: (r["evaluador_key"], r["evaluado_key"]),
                axis=1,
            ).tolist()
        )

    summary_rows = []
    details = {}

    all_people = participantes.to_dict("records")
    non_dg_people = [p for p in all_people if p["key"] != dg_key]

    for person in all_people:
        nombre = str(person["Nombre"]).strip()
        cargo = str(person["Cargo"]).strip()
        person_key = person["key"]
        is_dg = person_key == dg_key

        auto_done = (person_key, person_key) in done_pairs

        if is_dg:
            superior_state = "—"
            par_state = "—"

            missing_sub = [
                f"{p['Nombre']} ({p['Cargo']})"
                for p in non_dg_people
                if (person_key, p["key"]) not in done_pairs
            ]
            sub_done = len(missing_sub) == 0
            missing_sup = []
            missing_par = []
        else:
            superior_done = (person_key, dg_key) in done_pairs
            par_done = False
            sub_done = False

            superior_state = _icon(superior_done)
            par_state = _icon(par_done)

            missing_sup = [] if superior_done else [f"{dg['Nombre']} ({dg['Cargo']})"]
            missing_par = ["Pendiente de levantar en la evaluación"]
            missing_sub = ["Pendiente de levantar en la evaluación"]

        row = {
            "Nombre": nombre,
            "Autopercepción": _icon(auto_done),
            "Superior": superior_state,
            "Par": par_state,
            "Subordinado": _icon(sub_done),
        }

        has_pending = False
        if row["Autopercepción"] == "❌":
            has_pending = True
        if row["Superior"] == "❌":
            has_pending = True
        if row["Par"] == "❌":
            has_pending = True
        if row["Subordinado"] == "❌":
            has_pending = True

        row["_has_pending"] = has_pending
        summary_rows.append(row)

        details[nombre] = {
            "cargo": cargo,
            "faltantes": {
                "Autopercepción": [] if auto_done else [f"{nombre} ({cargo})"],
                "Superior": missing_sup,
                "Par": missing_par,
                "Subordinado": missing_sub,
            }
        }

    summary = pd.DataFrame(summary_rows)
    return summary, details


def render_tracking_table(df_respuestas: pd.DataFrame, df_participantes: pd.DataFrame, show_detail: bool):
    st.subheader("🧭 Encuestas faltantes")

    if df_participantes.empty:
        st.warning("Crea la pestaña Participantes con columnas Nombre y Cargo.")
        return

    tracking_df, tracking_details = build_tracking(df_respuestas, df_participantes)

    if tracking_df.empty:
        st.warning("No se pudo construir la tabla de seguimiento. Revisa Participantes.")
        return

    vista = st.selectbox("Vista:", ["Ver todo", "Ver pendientes"], key=f"vista_tracking_{show_detail}")

    if vista == "Ver pendientes":
        tracking_view = tracking_df[tracking_df["_has_pending"]].copy()
    else:
        tracking_view = tracking_df.copy()

    st.dataframe(
        tracking_view[["Nombre", "Autopercepción", "Superior", "Par", "Subordinado"]],
        hide_index=True,
        use_container_width=True,
    )

    if show_detail:
        st.markdown("### Ver detalle")
        for _, row in tracking_view.iterrows():
            nombre = row["Nombre"]
            info = tracking_details.get(nombre, {})
            cargo = info.get("cargo", "")
            faltantes = info.get("faltantes", {})

            with st.expander(f"{nombre} — {cargo}"):
                for bloque in ["Autopercepción", "Superior", "Par", "Subordinado"]:
                    st.write(f"**{bloque}:**")
                    items = faltantes.get(bloque, [])
                    if items:
                        for item in items:
                            st.write(f"- {item}")
                    else:
                        st.write("- Completo")


def main():
    st.set_page_config(page_title="Hogan 360 - Loguerkim", layout="wide")

    if "sync_done" not in st.session_state:
        sync_users()
        st.session_state["sync_done"] = True

    col_logo, col_titulo = st.columns([1, 3])
    with col_logo:
        try:
            st.image("logologuerkim.PNG", width=250)
        except Exception:
            st.warning("Logo no encontrado")
    with col_titulo:
        st.markdown(
            "<h1 style='padding-top: 20px;'>Resultados de encuesta 360 Loguerkim</h1>",
            unsafe_allow_html=True,
        )
    st.divider()

    try:
        df = get_drive_data()
        df_accesos = get_accesos_data()
        df_participantes = get_participantes_data()
    except Exception as e:
        st.error(f"Error de conexión: {e}")
        return

    tab1, tab2, tab3 = st.tabs([
        "👤 Mi Reporte Individual",
        "📊 Dashboard CEO",
        "📋 Encuestas faltantes",
    ])

    with tab1:
        if "user_auth" not in st.session_state:
            st.session_state["user_auth"] = False
            st.session_state["user_name"] = ""

        if not st.session_state["user_auth"]:
            st.header("Consulta de Resultados")

            if df_accesos.empty or "Nombre" not in df_accesos.columns or "Contraseña" not in df_accesos.columns:
                st.error("La pestaña Accesos debe tener columnas: Nombre, Cargo, Contraseña.")
            else:
                nombres = sorted(df_accesos["Nombre"].astype(str).str.strip().unique().tolist())

                c1, c2 = st.columns(2)
                with c1:
                    nombre_in = st.selectbox("Selecciona tu nombre:", nombres)
                with c2:
                    pass_in = st.text_input("Introduce tu contraseña:", type="password").strip()

                if st.button("Generar Reporte"):
                    if nombre_in and pass_in:
                        sync_users()
                        st.cache_data.clear()
                        df_accesos = get_accesos_data()

                        match_acc = df_accesos[
                            (df_accesos["Nombre"].astype(str).str.strip() == nombre_in) &
                            (df_accesos["Contraseña"].astype(str).str.strip() == pass_in)
                        ]

                        if not match_acc.empty:
                            st.session_state["user_auth"] = True
                            st.session_state["user_name"] = nombre_in
                            st.rerun()
                        else:
                            st.error("Nombre o contraseña incorrectos.")
                    else:
                        st.warning("Por favor, ingresa tus credenciales.")

        if st.session_state["user_auth"]:
            nombre = st.session_state["user_name"]

            c_welcome, c_logout = st.columns([4, 1])
            with c_welcome:
                st.success(f"✅ Bienvenido {nombre}, este es tu reporte")
            with c_logout:
                if st.button("Cerrar Sesión"):
                    st.session_state["user_auth"] = False
                    st.session_state["user_name"] = ""
                    st.rerun()

            res = process_hogan_logic(df, nombre, MAPEO_HOGAN)

            fig = go.Figure()
            fig.add_trace(go.Bar(x=res["Categoría"], y=res["Autoevaluación"], name="Mi Autoevaluación", marker_color="#1E40AF"))
            fig.add_trace(go.Bar(x=res["Categoría"], y=res["Superior"], name="Jefes (Superior)", marker_color="#F59E0B"))
            fig.add_trace(go.Bar(x=res["Categoría"], y=res["Par"], name="Pares (Colegas)", marker_color="#10B981"))
            fig.add_trace(go.Bar(x=res["Categoría"], y=res["Subordinado"], name="Reportes (Subordinados)", marker_color="#8B5CF6"))
            fig.update_layout(
                yaxis_range=[1, 7],
                barmode="group",
                legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
            )
            st.plotly_chart(fig, use_container_width=True)

            st.dataframe(
                res.style.format({
                    "Cobertura": "{:.0%}",
                    "Autoevaluación": "{:.2f}",
                    "Superior": "{:.2f}",
                    "Par": "{:.2f}",
                    "Subordinado": "{:.2f}",
                }),
                hide_index=True,
                use_container_width=True,
            )

            st.divider()
            st.subheader("🗣️ Comentarios Cualitativos Anónimos")
            st.dataframe(get_anonymous_feedback(df, nombre), use_container_width=True, hide_index=True)

            render_glosario()

    with tab2:
        st.header("Dashboard Administrativo")

        if st.button("🔄 Sincronizar Usuarios con Participantes"):
            with st.spinner("Sincronizando..."):
                m = sync_users()
                st.cache_data.clear()
                st.info(m)

        if not st.session_state.get("ceo_auth", False):
            pw = st.text_input("Contraseña CEO:", type="password")
            if st.button("Acceder Dashboard"):
                if pw == PASSWORD_CEO:
                    st.session_state["ceo_auth"] = True
                    st.rerun()
                else:
                    st.error("Acceso denegado")
        else:
            st.divider()
            st.subheader("📌 Benchmark Organizacional (Promedio Global)")
            glob = get_global_metrics(df, MAPEO_HOGAN)

            fig_glob = go.Figure()
            fig_glob.add_trace(go.Bar(x=glob["Categoría"], y=glob["Autoevaluación"], name="Autoevaluación", marker_color="#1E40AF"))
            fig_glob.add_trace(go.Bar(x=glob["Categoría"], y=glob["Superior"], name="Superior", marker_color="#F59E0B"))
            fig_glob.add_trace(go.Bar(x=glob["Categoría"], y=glob["Par"], name="Par", marker_color="#10B981"))
            fig_glob.add_trace(go.Bar(x=glob["Categoría"], y=glob["Subordinado"], name="Subordinado", marker_color="#8B5CF6"))
            fig_glob.update_layout(
                yaxis_range=[1, 7],
                barmode="group",
                legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
            )
            st.plotly_chart(fig_glob, use_container_width=True)
            st.table(glob)

            st.divider()
            render_tracking_table(df, df_participantes, show_detail=True)

            st.divider()
            st.subheader("🔍 Auditoría por Líder")
            lideres = sorted(df[COL_EVALUADO].astype(str).str.strip().unique().tolist())
            lider_sel = st.selectbox("Selecciona un líder para auditar:", lideres)

            if lider_sel:
                res_l = process_hogan_logic(df, lider_sel, MAPEO_HOGAN)

                fig_l = go.Figure()
                fig_l.add_trace(go.Bar(x=res_l["Categoría"], y=res_l["Autoevaluación"], name="Autoevaluación", marker_color="#1E40AF"))
                fig_l.add_trace(go.Bar(x=res_l["Categoría"], y=res_l["Superior"], name="Superior", marker_color="#F59E0B"))
                fig_l.add_trace(go.Bar(x=res_l["Categoría"], y=res_l["Par"], name="Par", marker_color="#10B981"))
                fig_l.add_trace(go.Bar(x=res_l["Categoría"], y=res_l["Subordinado"], name="Subordinado", marker_color="#8B5CF6"))
                fig_l.update_layout(
                    title=f"Resultados: {lider_sel}",
                    yaxis_range=[1, 7],
                    barmode="group",
                    legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
                )
                st.plotly_chart(fig_l, use_container_width=True)

                st.dataframe(
                    res_l.style.format({
                        "Cobertura": "{:.0%}",
                        "Autoevaluación": "{:.2f}",
                        "Superior": "{:.2f}",
                        "Par": "{:.2f}",
                        "Subordinado": "{:.2f}",
                    }),
                    hide_index=True,
                    use_container_width=True,
                )

                st.subheader(f"Comentarios para {lider_sel}")
                st.dataframe(get_anonymous_feedback(df, lider_sel), use_container_width=True, hide_index=True)

            render_glosario()

    with tab3:
        render_tracking_table(df, df_participantes, show_detail=False)


if __name__ == "__main__":
    main()
