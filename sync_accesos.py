# sync_accesos.py

import streamlit as st
import pandas as pd
import random
import gspread
from google.oauth2.service_account import Credentials
from import_data import SHEET_ID


def _norm(x):
    return str(x).strip().lower()


def _build_password(nombre):
    n = "".join(nombre.split())
    ini = n[:2] if len(n) >= 2 else "X"
    fin = n[-2:] if len(n) >= 2 else "X"
    num = random.randint(100, 999)
    return f"{ini}{num}{fin}"


def _get_client():
    scope = [
        "https://www.googleapis.com/auth/spreadsheets",
        "https://www.googleapis.com/auth/drive",
    ]

    creds_dict = dict(st.secrets["gcp_service_account"])
    raw_key = creds_dict["private_key"]
    creds_dict["private_key"] = raw_key.replace("\\n", "\n")

    creds = Credentials.from_service_account_info(creds_dict, scopes=scope)
    return gspread.authorize(creds)


def sync_users():
    try:
        client = _get_client()
        spreadsheet = client.open_by_key(SHEET_ID)

        # --- PARTICIPANTES ---
        sheet_part = spreadsheet.worksheet("Participantes")
        df_part = pd.DataFrame(sheet_part.get_all_records())

        if df_part.empty:
            return "❌ Participantes vacío"

        # --- ACCESOS ---
        try:
            sheet_acc = spreadsheet.worksheet("Accesos")
            df_acc = pd.DataFrame(sheet_acc.get_all_records())
        except:
            sheet_acc = spreadsheet.add_worksheet(title="Accesos", rows="100", cols="3")
            sheet_acc.update("A1:C1", [["Nombre", "Cargo", "Contraseña"]])
            df_acc = pd.DataFrame(columns=["Nombre", "Cargo", "Contraseña"])

        # --- KEYS EXISTENTES ---
        existentes = set()
        if not df_acc.empty:
            existentes = set(
                df_acc.apply(
                    lambda r: f"{_norm(r['Nombre'])}|||{_norm(r['Cargo'])}",
                    axis=1,
                )
            )

        # --- NUEVOS ---
        nuevos = []

        for _, row in df_part.iterrows():
            nombre = str(row["Nombre"]).strip()
            cargo = str(row["Cargo"]).strip()

            key = f"{_norm(nombre)}|||{_norm(cargo)}"

            if key not in existentes:
                password = _build_password(nombre)
                nuevos.append([nombre, cargo, password])

        # --- INSERTAR SOLO SI HAY NUEVOS ---
        if nuevos:
            sheet_acc.append_rows(nuevos)
            return f"✅ {len(nuevos)} accesos creados"
        else:
            return "ℹ️ Sin cambios (ya existían)"

    except Exception as e:
        return f"❌ Error: {str(e)}"
