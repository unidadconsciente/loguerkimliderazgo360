import streamlit as st

SHEET_ID = "1MTuLBBk_-l5QRffFEktVZG_6pFwvl4SfshKTgVkd09s"
MIN_OBS = 3  
PASSWORD_CEO = "Liderazgo2026"

# Mapeo oficial
MAPEO_HOGAN = {
    "Autogestión (Self-Management)": list(range(1, 11)),
    "Gestión de Relaciones": list(range(11, 26)),
    "Trabajo en el Negocio": list(range(26, 43)),
    "Trabajo sobre el Negocio": list(range(43, 51))
}

GLOSARIO = {
    "Cobertura": "Porcentaje de conductas del dominio que recibieron respuestas suficientes (mínimo 3 evaluadores).",
    "Calidad": "Nivel de representatividad estadística. Sólido (>80%), Cautela (50-80%), Insuficiente (<50%)."
}
