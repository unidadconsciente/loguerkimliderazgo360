import streamlit as st
import plotly.graph_objects as go
import pandas as pd
import unicodedata

from sheet_acces import get_drive_data, get_accesos_data, get_participantes_data
from calculos import process_hogan_logic, get_global_metrics, get_anonymous_feedback
from import_data import PASSWORD_CEO, GLOSARIO, MAPEO_HOGAN
from sync_accesos import sync_users


COL_NOMBRE_EVALUADOR = "Tu Nombre (Evaluador)"
COL_CARGO_EVALUADOR = "Tu Cargo"
COL_EVALUADO = "Nombre de la persona Evaluada"
COL_CARGO_EVALUADO = "Cargo del Evaluado"
COL_RELACION = "Tu relación con el evaluado"

REL_AUTO = "autoevaluacion"
REL_SUPERIOR = "subordinado (el/ella es mi jefe)"
REL_SUBORDINADO = "superior (yo soy su jefe)"
REL_PAR = "par"


def _norm(value: str) -> str:
    text = str(value).strip().lower()
    text = unicodedata.normalize("NFKD", text)
    return "".join(ch for ch in text if not unicodedata.combining(ch))


def _flag_to_mode(value: str) -> str:
    v = _norm(value)
    if v == "si":
        return "si"
    if v == "no":
        return "no"
    return "na"


def _icon(done: bool) -> str:
    return "✅" if done else "❌"


def _display_for_ver_todo(flag_mode: str, done: bool) -> str:
    if flag_mode != "si":
        return "—"
    return _icon(done)


def _pair_key(nombre: str, cargo: str) -> str:
    return f"{_norm(nombre)}|||{_norm(cargo)}"


def _is_dg(cargo: str) -> bool:
    return _norm(cargo) == "director general"


def render_glosario():
    st.markdown("---")
    with st.expander("🔎 Glosario de términos y Metodología"):
        st.write("### 📊 Indicadores de Validez")
        st.write(
            "**Cobertura:** Muestra qué tanto feedback recibiste en cada área. "
            "Es el porcentaje de conductas (preguntas) de esa categoría que tus evaluadores sí contestaron."
        )
        st.write("**Calidad:** Nivel de representatividad estadística basada en la cobertura.")
        st.write("- 🟢 **Sólido (>80%):** Feedback completo. Datos seguros.")
        st.write("- 🟡 **Cautela (50-80%):** Faltan respuestas; usar como guía parcial.")
        st.write("- 🔴 **Insuficiente (<50%):** Base débil; promedios posiblemente sesgados.")
        st.markdown("---")
        for term, desc in GLOSARIO.items():
            if term not in ["Calidad", "Cobertura"]:
                st.write(f"**{term}:** {desc}")


def _prepare_participantes(df_part: pd.DataFrame) -> pd.DataFrame:
    if df_part.empty:
        return pd.DataFrame()

    required = ["Nombre", "Cargo", "Autoevaluación", "Superior", "Par", "Subordinado"]
    if not set(required).issubset(df_part.columns):
        return pd.DataFrame()

    part = df_part.copy()
    for col in required:
        part[col] = part[col].astype(str).str.strip()

    part["key"] = part.apply(lambda r: _pair_key(r["Nombre"], r["Cargo"]), axis=1)
    part["cargo_key"] = part["Cargo"].apply(_norm)
    part["nombre_key"] = part["Nombre"].apply(_norm)

    part["auto_flag"] = part["Autoevaluación"].apply(_flag_to_mode)
    part["sup_flag"] = part["Superior"].apply(_flag_to_mode)
    part["par_flag"] = part["Par"].apply(_flag_to_mode)
    part["sub_flag"] = part["Subordinado"].apply(_flag_to_mode)

    part = part.drop_duplicates(subset=["key"], keep="first").copy()
    return part


def _prepare_respuestas(df_resp: pd.DataFrame) -> pd.DataFrame:
    if df_resp.empty:
        return pd.DataFrame()

    df = df_resp.copy()

    for col in [COL_NOMBRE_EVALUADOR, COL_CARGO_EVALUADOR, COL_EVALUADO, COL_CARGO_EVALUADO, COL_RELACION]:
        if col not in df.columns:
            df[col] = ""

    df[COL_NOMBRE_EVALUADOR] = df[COL_NOMBRE_EVALUADOR].astype(str).str.strip()
    df[COL_CARGO_EVALUADOR] = df[COL_CARGO_EVALUADOR].astype(str).str.strip()
    df[COL_EVALUADO] = df[COL_EVALUADO].astype(str).str.strip()
    df[COL_CARGO_EVALUADO] = df[COL_CARGO_EVALUADO].astype(str).str.strip()
    df[COL_RELACION] = df[COL_RELACION].astype(str).str.strip()

    df["evaluador_key"] = df.apply(
        lambda r: _pair_key(r.get(COL_NOMBRE_EVALUADOR, ""), r.get(COL_CARGO_EVALUADOR, "")),
        axis=1,
    )
    df["evaluado_key"] = df.apply(
        lambda r: _pair_key(r.get(COL_EVALUADO, ""), r.get(COL_CARGO_EVALUADO, "")),
        axis=1,
    )
    df["evaluador_cargo_key"] = df[COL_CARGO_EVALUADOR].apply(_norm)
    df["evaluado_cargo_key"] = df[COL_CARGO_EVALUADO].apply(_norm)
    df["evaluado_nombre_key"] = df[COL_EVALUADO].apply(_norm)
    df["rel_norm"] = df[COL_RELACION].apply(_norm)

    if "Timestamp" in df.columns:
        df["Timestamp"] = pd.to_datetime(df["Timestamp"], errors="coerce")
        df = df.sort_values("Timestamp").drop_duplicates(
            subset=["evaluador_key", "evaluado_key", "rel_norm"],
            keep="last",
        )
    else:
        df = df.drop_duplicates(
            subset=["evaluador_key", "evaluado_key", "rel_norm"],
            keep="last",
        )

    return df


def build_tracking(df_resp: pd.DataFrame, df_part: pd.DataFrame):
    participantes = _prepare_participantes(df_part)
    respuestas = _prepare_respuestas(df_resp)

    if participantes.empty:
        return pd.DataFrame(), {}

    summary_rows = []
    details = {}

    for _, row in participantes.iterrows():
        nombre = row["Nombre"]
        cargo = row["Cargo"]
        person_key = row["key"]

        auto_flag = row["auto_flag"]
        sup_flag = row["sup_flag"]
        par_flag = row["par_flag"]
        sub_flag = row["sub_flag"]

        auto_done = False
        superior_done = False
        par_done = False
        subordinado_done = False
        faltantes_subordinado = []

        # AUTOEVALUACIÓN: por persona
        if auto_flag == "si":
            auto_done = not respuestas[
                (respuestas["evaluador_key"] == person_key) &
                (
                    (respuestas["rel_norm"] == REL_AUTO) |
                    (
                        (respuestas["evaluador_key"] == respuestas["evaluado_key"])
                    )
                )
            ].empty

        # SUPERIOR: si en Participantes dice "Sí",
        # debe existir una respuesta de esa persona con relación "Subordinado (él/ella es mi jefe)"
        if sup_flag == "si":
            superior_done = not respuestas[
                (respuestas["evaluador_key"] == person_key) &
                (respuestas["rel_norm"] == REL_SUPERIOR)
            ].empty

        # PAR: por persona
        if par_flag == "si":
            par_done = not respuestas[
                (respuestas["evaluador_key"] == person_key) &
                (respuestas["rel_norm"].str.startswith(REL_PAR))
            ].empty

        # SUBORDINADO:
        # regla general: si en Participantes dice "Sí", debe existir una respuesta
        # de esa persona con relación "Superior (yo soy su jefe)"
        if sub_flag == "si":
            subordinado_done = not respuestas[
                (respuestas["evaluador_key"] == person_key) &
                (respuestas["rel_norm"] == REL_SUBORDINADO)
            ].empty

            # Regla especial actual: solo Director General debe evaluar a todos
            if _is_dg(cargo):
                expected_people = participantes.loc[
                    participantes["cargo_key"] != _norm(cargo),
                    ["Nombre", "Cargo", "nombre_key"],
                ].drop_duplicates().copy()

                hechas = respuestas[
                    (respuestas["evaluador_key"] == person_key) &
                    (respuestas["rel_norm"] == REL_SUBORDINADO) &
                    (respuestas["evaluado_cargo_key"] != _norm(cargo))
                ]["evaluado_nombre_key"].dropna().unique().tolist()

                hechas_set = set(hechas)
                expected_set = set(expected_people["nombre_key"].tolist())
                faltantes_keys = expected_set - hechas_set

                faltantes_subordinado = (
                    expected_people[expected_people["nombre_key"].isin(faltantes_keys)]
                    .apply(lambda r: f"{r['Nombre']} ({r['Cargo']})", axis=1)
                    .tolist()
                )

                subordinado_done = len(faltantes_subordinado) == 0

        summary_rows.append(
            {
                "Nombre": nombre,
                "Autoevaluación": _display_for_ver_todo(auto_flag, auto_done),
                "Superior": _display_for_ver_todo(sup_flag, superior_done),
                "Par": _display_for_ver_todo(par_flag, par_done),
                "Subordinado": _display_for_ver_todo(sub_flag, subordinado_done),
            }
        )

        details[nombre] = {
            "cargo": cargo,
            "faltantes_subordinado": faltantes_subordinado,
            "aplica_subordinado": sub_flag == "si",
        }

    df_all = pd.DataFrame(summary_rows)
    return df_all, details


def render_tracking_tables(df_respuestas: pd.DataFrame, df_participantes: pd.DataFrame, show_detail: bool):
    st.subheader("🧭 Encuestas faltantes")

    df_all, details = build_tracking(df_respuestas, df_participantes)

    if df_all.empty:
        st.warning(
            "Revisa la pestaña Participantes. Debe tener columnas exactas: "
            "Nombre, Cargo, Autoevaluación, Superior, Par, Subordinado."
        )
        return

    st.dataframe(
        df_all[["Nombre", "Autoevaluación", "Superior", "Par", "Subordinado"]],
        hide_index=True,
        use_container_width=True,
    )

    if show_detail:
        st.markdown("### Ver detalle por persona")
        persona = st.selectbox(
            "Selecciona una persona para ver detalle:",
            df_all["Nombre"].tolist(),
            key="detalle_tracking_persona",
        )

        info = details.get(persona, {})
        cargo = info.get("cargo", "")
        aplica_subordinado = info.get("aplica_subordinado", False)
        faltantes = info.get("faltantes_subordinado", [])

        st.markdown(f"**{persona} — {cargo}**")

        if not aplica_subordinado:
            st.info("A esta persona no le aplica evaluación a subordinados según la hoja Participantes.")
        else:
            if faltantes:
                st.write("**Le falta evaluar a:**")
                for item in faltantes:
                    st.write(f"- {item}")
            else:
                st.success("Completó la evaluación de todos sus subordinados.")


def main():
    st.set_page_config(page_title="Hogan 360 - Loguerkim", layout="wide")

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

            if df_accesos.empty or not {"Nombre", "Cargo", "Contraseña"}.issubset(df_accesos.columns):
                st.error("La pestaña Accesos debe tener columnas exactas: Nombre, Cargo, Contraseña.")
            else:
                df_acc = df_accesos.copy()
                df_acc["Nombre"] = df_acc["Nombre"].astype(str).str.strip()
                df_acc["Cargo"] = df_acc["Cargo"].astype(str).str.strip()
                df_acc["Contraseña"] = df_acc["Contraseña"].astype(str).str.strip()
                df_acc["label"] = df_acc["Nombre"] + " — " + df_acc["Cargo"]

                labels = sorted(df_acc["label"].unique().tolist())

                c1, c2 = st.columns(2)
                with c1:
                    selected_label = st.selectbox("Selecciona tu nombre:", labels)
                with c2:
                    pass_in = st.text_input("Introduce tu contraseña:", type="password").strip()

                if st.button("Generar Reporte"):
                    if selected_label and pass_in:
                        match_acc = df_acc[
                            (df_acc["label"] == selected_label) &
                            (df_acc["Contraseña"] == pass_in)
                        ]

                        if not match_acc.empty:
                            st.session_state["user_auth"] = True
                            st.session_state["user_name"] = match_acc.iloc[0]["Nombre"]
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

        if st.button("Sincronizar accesos"):
            msg = sync_users()
            st.cache_data.clear()
            st.info(msg)

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
            render_tracking_tables(df, df_participantes, show_detail=True)

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
        render_tracking_tables(df, df_participantes, show_detail=True)


if __name__ == "__main__":
    main()
