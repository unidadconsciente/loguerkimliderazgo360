import streamlit as st
import pandas as pd
import random
import gspread
from google.oauth2.service_account import Credentials
from import_data import SHEET_ID

def sync_users():
    # Conexión técnica reusando tus secretos de Streamlit
    scope = ["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"]
    creds_dict = dict(st.secrets["gcp_service_account"])
    raw_key = creds_dict["private_key"]
    creds_dict["private_key"] = raw_key.replace("\\n", "\n").strip().strip("'").strip('"')
    creds = Credentials.from_service_account_info(creds_dict, scopes=scope)
    client = gspread.authorize(creds)
    spreadsheet = client.open_by_key(SHEET_ID)

    # 1. Obtener datos de Respuestas y Accesos (Columnas: Nombre, Correo, Contraseña)
    sheet_resp = spreadsheet.get_worksheet(0) 
    df_resp = pd.DataFrame(sheet_resp.get_all_records())
    
    try:
        sheet_acc = spreadsheet.worksheet("Accesos")
    except:
        sheet_acc = spreadsheet.add_worksheet(title="Accesos", rows="100", cols="3")
        sheet_acc.update('A1:C1', [['Nombre', 'Correo', 'Contraseña']])
    
    df_acc = pd.DataFrame(sheet_acc.get_all_records())

    # 2. Identificar correos únicos que no están en Accesos
    df_resp_unicos = df_resp.drop_duplicates('Tu Correo Electrónico', keep='last')
    
    nuevos_datos = []
    for _, row in df_resp_unicos.iterrows():
        correo = str(row['Tu Correo Electrónico']).strip().lower()
        nombre = str(row['Tu Nombre (Evaluador)']).strip()
        
        if correo not in df_acc['Correo'].str.lower().values:
            # Lógica de contraseña: 2 letras inicio + 3 num + 2 letras final
            p_inicio = nombre[:2].replace(" ", "X")
            p_final = nombre[-2:].replace(" ", "X")
            num_rand = random.randint(100, 999)
            password = f"{p_inicio}{num_rand}{p_final}"
            
            nuevos_datos.append([nombre, correo, password])

    # 3. Guardar solo los nuevos registros
    if nuevos_datos:
        sheet_acc.append_rows(nuevos_datos)
        st.success(f"Se sincronizaron {len(nuevos_datos)} usuarios nuevos.")
    else:
        st.info("No hay usuarios nuevos por registrar.")

if __name__ == "__main__":
    sync_users()
