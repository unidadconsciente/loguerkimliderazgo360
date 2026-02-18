import streamlit as st
import pandas as pd
import gspread
from google.oauth2.service_account import Credentials

# Importamos SHEET_ID desde import_data para mantener una sola fuente de verdad
from import_data import SHEET_ID

@st.cache_data(ttl=600)
def get_drive_data():
    """Conecta con Google Drive usando el Service Account en Secrets."""
    scope = ["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"]
    creds = Credentials.from_service_account_info(st.secrets["gcp_service_account"], scopes=scope)
    client = gspread.authorize(creds)
    
    sheet = client.open_by_key(SHEET_ID).sheet1
    df = pd.DataFrame(sheet.get_all_records())
    
    for col in df.columns:
        if col.split('.')[0].strip().isdigit():
            df[col] = pd.to_numeric(df[col], errors='coerce')
    return df
