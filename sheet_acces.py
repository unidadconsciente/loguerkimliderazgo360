import streamlit as st
import pandas as pd
import gspread
from google.oauth2.service_account import Credentials

# Importamos SHEET_ID desde import_data para mantener una sola fuente de verdad
from import_data import SHEET_ID

@st.cache_data(ttl=600)
def get_drive_data():
    scope = [
        "https://www.googleapis.com/auth/spreadsheets",
        "https://www.googleapis.com/auth/drive"
    ]

    # Convertimos Secrets en dict editable
    creds_dict = dict(st.secrets["gcp_service_account"])

    # 🔴 FIX CRÍTICO: reconstruir saltos de línea reales del PEM
    creds_dict["private_key"] = creds_dict["private_key"].replace("\\n", "\n")

    # Crear credenciales válidas
    creds = Credentials.from_service_account_info(creds_dict, scopes=scope)

    client = gspread.authorize(creds)

    sheet = client.open_by_key(SHEET_ID).sheet1
    df = pd.DataFrame(sheet.get_all_records())

    # Limpieza numérica
    for col in df.columns:
        if col.split('.')[0].strip().isdigit():
            df[col] = pd.to_numeric(df[col], errors='coerce')

    return df
