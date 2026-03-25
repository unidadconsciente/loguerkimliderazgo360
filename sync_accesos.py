import streamlit as st
import pandas as pd
import random
import gspread
from google.oauth2.service_account import Credentials
from import_data import SHEET_ID


def _norm(value: str) -> str:
    return str(value).strip().lower()


def _build_password(nombre: str) -> str:
    n_clean = "".join(str(nombre).split())
    p_inicio = n_clean[:2] if len(n_clean) >= 2 else "X"
    p_final = n_clean[-2:] if len(n_clean) >= 2 else "X"
    num_rand = random.randint(100, 999)
    return f"{p_inicio}{num_rand}{p_final}"


def get_gspread_client():
    scope = [
        "https://www.googleapis.com/auth/spreadsheets",
        "https://www.googleapis.com/auth/drive",
    ]
    creds_dict = dict(st.secrets["gcp_service_account"])
    raw_key = creds_dict["private_key"]
    creds_dict["private_key"] = raw_key.replace("\\n", "\n").strip().strip("'").strip('"')
    creds = Credentials.from_service_account_info(creds_dict, scopes=scope)
    return gspread.authorize(creds)


def sync_users():
    try:
        client = get_gspread_client()
        spreadsheet = client.open_by_key(SHEET_ID)

        try:
            sheet_part = spreadsheet.worksheet("Participantes")
        except Exception:
            return "❌ No existe la pestaña Participantes."

        df_part = pd.DataFrame(sheet_part.get_all_records())
        if df_part.empty or "Nombre" not in df_part.columns or "Cargo" not in df_part.columns:
            return "❌ La pestaña Participantes debe tener columnas: Nombre, Cargo."

        try:
            sheet_acc = spreadsheet.worksheet("Accesos")
        except Exception:
            sheet_acc = spreadsheet.add_worksheet(title="Accesos", rows="100", cols="3")
            sheet_acc.update("A1:C1", [["Nombre", "Cargo", "Contraseña"]])

        df_acc = pd.DataFrame(sheet_acc.get_all_records())

        existentes = set()
        if not df_acc.empty and {"Nombre", "Cargo"}.issubset(df_acc.columns):
            existentes = set(
                df_acc.apply(
                    lambda r: f"{_norm(r['Nombre'])}|||{_norm(r['Cargo'])}",
                    axis=1,
                ).tolist()
            )

        nuevos_registros = []
        for _, row in df_part.iterrows():
            nombre = str(row.get("Nombre", "")).strip()
            cargo = str(row.get("Cargo", "")).strip()

            if not nombre or not cargo:
                continue

            key = f"{_norm(nombre)}|||{_norm(cargo)}"
            if key not in existentes:
                password = _build_password(nombre)
                nuevos_registros.append([nombre, cargo, password])

        if nuevos_registros:
            sheet_acc.append_rows(nuevos_registros)
            return f"✅ Sincronizados {len(nuevos_registros)} nuevos accesos desde Participantes."

        return "ℹ️ No se detectaron participantes nuevos para Accesos."

    except Exception as e:
        return f"❌ Error en Drive: {str(e)}"
