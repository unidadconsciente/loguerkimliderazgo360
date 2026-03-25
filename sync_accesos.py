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


def _get_client():
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
        client = _get_client()
        spreadsheet = client.open_by_key(SHEET_ID)

        # Participantes = fuente de verdad
        sheet_part = spreadsheet.worksheet("Participantes")
        df_part = pd.DataFrame(sheet_part.get_all_records())

        if df_part.empty:
            return "❌ La pestaña Participantes está vacía."

        required_part = {"Nombre", "Cargo"}
        if not required_part.issubset(df_part.columns):
            return "❌ Participantes debe tener columnas: Nombre, Cargo."

        df_part = df_part.copy()
        df_part["Nombre"] = df_part["Nombre"].astype(str).str.strip()
        df_part["Cargo"] = df_part["Cargo"].astype(str).str.strip()

        # Accesos
        try:
            sheet_acc = spreadsheet.worksheet("Accesos")
            df_acc = pd.DataFrame(sheet_acc.get_all_records())
        except Exception:
            sheet_acc = spreadsheet.add_worksheet(title="Accesos", rows="200", cols="3")
            sheet_acc.update("A1:C1", [["Nombre", "Cargo", "Contraseña"]])
            df_acc = pd.DataFrame(columns=["Nombre", "Cargo", "Contraseña"])

        if df_acc.empty:
            df_acc = pd.DataFrame(columns=["Nombre", "Cargo", "Contraseña"])
        else:
            required_acc = {"Nombre", "Cargo", "Contraseña"}
            if not required_acc.issubset(df_acc.columns):
                return "❌ Accesos debe tener columnas: Nombre, Cargo, Contraseña."

            df_acc = df_acc.copy()
            df_acc["Nombre"] = df_acc["Nombre"].astype(str).str.strip()
            df_acc["Cargo"] = df_acc["Cargo"].astype(str).str.strip()
            df_acc["Contraseña"] = df_acc["Contraseña"].astype(str).str.strip()

        existentes = set(
            df_acc.apply(
                lambda r: f"{_norm(r['Nombre'])}|||{_norm(r['Cargo'])}",
                axis=1,
            ).tolist()
        ) if not df_acc.empty else set()

        nuevos_registros = []
        for _, row in df_part.iterrows():
            nombre = row["Nombre"]
            cargo = row["Cargo"]

            if not nombre or not cargo:
                continue

            key = f"{_norm(nombre)}|||{_norm(cargo)}"
            if key not in existentes:
                password = _build_password(nombre)
                nuevos_registros.append([nombre, cargo, password])
                existentes.add(key)

        if nuevos_registros:
            sheet_acc.append_rows(nuevos_registros)
            return f"✅ {len(nuevos_registros)} accesos creados."

        return "ℹ️ Sin cambios. Todos los accesos ya existían."

    except Exception as e:
        return f"❌ Error en Drive: {str(e)}"
