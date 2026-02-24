import streamlit as st
import pandas as pd
import random
import gspread
from google.oauth2.service_account import Credentials
from import_data import SHEET_ID

def get_gspread_client():
    scope = ["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"]
    creds_dict = dict(st.secrets["gcp_service_account"])
    raw_key = creds_dict["private_key"]
    creds_dict["private_key"] = raw_key.replace("\\n", "\n").strip().strip("'").strip('"')
    creds = Credentials.from_service_account_info(creds_dict, scopes=scope)
    return gspread.authorize(creds)

def sync_users():
    try:
        client = get_gspread_client()
        spreadsheet = client.open_by_key(SHEET_ID)
        
        # 1. Leer Respuestas y Accesos (Columnas exactas solicitadas)
        sheet_resp = spreadsheet.get_worksheet(0) 
        df_resp = pd.DataFrame(sheet_resp.get_all_records())
        
        try:
            sheet_acc = spreadsheet.worksheet("Accesos")
        except:
            sheet_acc = spreadsheet.add_worksheet(title="Accesos", rows="100", cols="3")
            sheet_acc.update('A1:C1', [['Nombre', 'Correo', 'Contraseña']])
        
        df_acc = pd.DataFrame(sheet_acc.get_all_records())

        # 2. Limpieza y Filtro de Únicos
        col_email_forms = "Tu Correo Electrónico"
        col_nombre_forms = "Tu Nombre (Evaluador)"
        
        df_resp[col_email_forms] = df_resp[col_email_forms].astype(str).str.strip().str.lower()
        df_unicos = df_resp.drop_duplicates(subset=[col_email_forms], keep='last')

        # Correos ya registrados en la pestaña Accesos
        existentes = set()
        if not df_acc.empty and 'Correo' in df_acc.columns:
            existentes = set(df_acc['Correo'].astype(str).str.strip().str.lower().tolist())

        nuevos_registros = []
        for _, row in df_unicos.iterrows():
            email = row[col_email_forms]
            nombre = str(row[col_nombre_forms]).strip()
            
            if email and email != 'nan' and email not in existentes:
                # REGLA: 2 letras inicio + 3 num + 2 letras final
                n_clean = nombre.replace(" ", "")
                p_inicio = n_clean[:2] if len(n_clean) >= 2 else "X"
                p_final = n_clean[-2:] if len(n_clean) >= 2 else "X"
                num_rand = random.randint(100, 999)
                password = f"{p_inicio}{num_rand}{p_final}"
                
                # Formato: [Nombre, Correo, Contraseña]
                nuevos_registros.append([nombre, email, password])

        if nuevos_registros:
            sheet_acc.append_rows(nuevos_registros)
            return f"✅ Sincronizados {len(nuevos_registros)} nuevos usuarios."
        return "ℹ️ No se detectaron usuarios nuevos en Form Responses 1."

    except Exception as e:
        return f"❌ Error en Drive: {str(e)}"
