@st.cache_data(ttl=600)
def get_drive_data():
    """Conecta con Google Drive usando el Service Account en Secrets."""
    scope = ["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"]
    # Reutiliza el JSON que ya tienes en tus Secrets de Streamlit
    creds = Credentials.from_service_account_info(st.secrets["gcp_service_account"], scopes=scope)
    client = gspread.authorize(creds)
    
    # Acceso al ID específico que proporcionaste
    sheet = client.open_by_key(SHEET_ID).sheet1
    df = pd.DataFrame(sheet.get_all_records())
    
    # Limpieza: Convertir ítems (identificados por 'N.') a numérico
    for col in df.columns:
        if col.split('.')[0].strip().isdigit():
            df[col] = pd.to_numeric(df[col], errors='coerce')
    return df
