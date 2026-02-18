import streamlit as st
import pandas as pd
import gspread
from google.oauth2.service_account import Credentials

# Importamos SHEET_ID desde import_data para mantener una sola fuente de verdad
from import_data import SHEET_ID

@st.cache_data(ttl=600)
def get_drive_data():
    scope = ["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"]
    
    # Extraemos el diccionario
    creds_dict = dict(st.secrets["gcp_service_account"])
    
    # LIMPIEZA TOTAL DE LA LLAVE
    # 1. Convertimos los \n de texto en saltos de línea reales
    # 2. Eliminamos espacios en blanco al inicio y final
    # 3. Quitamos posibles comillas accidentales
    raw_key = creds_dict["private_key"]
    clean_key = raw_key.replace("\\n", "\n").strip().strip("'").strip('"')
    creds_dict["private_key"] = clean_key
    
    try:
        creds = Credentials.from_service_account_info(creds_dict, scopes=scope)
        client = gspread.authorize(creds)
        
        sheet = client.open_by_key(SHEET_ID).sheet1
        df = pd.DataFrame(sheet.get_all_records())
        
        # Limpieza de ítems Hogan
        for col in df.columns:
            if col.split('.')[0].strip().isdigit():
                df[col] = pd.to_numeric(df[col], errors='coerce')
        return df
    except Exception as e:
        st.error(f"Error detallado en autenticación: {e}")
        raise e
