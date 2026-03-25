import streamlit as st
import pandas as pd
import gspread
from google.oauth2.service_account import Credentials
from import_data import SHEET_ID


def _get_client():
    scope = [
        "https://www.googleapis.com/auth/spreadsheets",
        "https://www.googleapis.com/auth/drive",
    ]

    creds_dict = dict(st.secrets["gcp_service_account"])
    raw_key = creds_dict["private_key"]
    clean_key = raw_key.replace("\\n", "\n").strip().strip("'").strip('"')
    creds_dict["private_key"] = clean_key

    creds = Credentials.from_service_account_info(creds_dict, scopes=scope)
    return gspread.authorize(creds)


@st.cache_data(ttl=600)
def get_drive_data():
    try:
        client = _get_client()
        sheet = client.open_by_key(SHEET_ID).sheet1
        df = pd.DataFrame(sheet.get_all_records())

        for col in df.columns:
            if str(col).split(".")[0].strip().isdigit():
                df[col] = pd.to_numeric(df[col], errors="coerce")

        return df
    except Exception as e:
        st.error(f"Error detallado en autenticación: {e}")
        raise e


@st.cache_data(ttl=60)
def get_accesos_data():
    try:
        client = _get_client()
        sheet = client.open_by_key(SHEET_ID).worksheet("Accesos")
        return pd.DataFrame(sheet.get_all_records())
    except Exception as e:
        st.error(f"Error cargando pestaña Accesos: {e}")
        return pd.DataFrame()


@st.cache_data(ttl=60)
def get_participantes_data():
    try:
        client = _get_client()
        sheet = client.open_by_key(SHEET_ID).worksheet("Participantes")
        return pd.DataFrame(sheet.get_all_records())
    except Exception as e:
        st.error(f"Error cargando pestaña Participantes: {e}")
        return pd.DataFrame()
