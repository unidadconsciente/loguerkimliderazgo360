import streamlit as st
import pandas as pd
import gspread
from google.oauth2.service_account import Credentials
import plotly.graph_objects as go

# --- CONFIGURACIÓN MAESTRA ---
SHEET_ID = "1MTuLBBk_-l5QRffFEktVZG_6pFwvl4SfshKTgVkd09s"
MIN_OBS = 3  # Umbral de suficiencia de observación
PASSWORD_CEO = "Liderazgo2026"

# --- MAPEO DE DOMINIOS (ADN HOGAN) ---
MAPEO_HOGAN = {
    "Self-Management": list(range(1, 11)),
    "Relationship Management": list(range(11, 26)),
    "Working in the Business": list(range(26, 43)),
    "Working on the Business": list(range(43, 51))
}
