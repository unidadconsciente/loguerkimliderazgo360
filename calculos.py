import pandas as pd
from import_data import MAPEO_HOGAN, MIN_OBS

def process_hogan_logic(df, nombre_evaluado):
    """Calcula métricas filtrando estrictamente por la persona evaluada."""
    # Filtrar TODO lo que pertenezca a este líder
    df_persona = df[df['Nombre de la persona Evaluada'] == nombre_evaluado]
    
    self_row = df_persona[df_persona['Tu relación con el evaluado'] == 'Self']
    others_data = df_persona[df_persona['Tu relación con el evaluado'] != 'Self']
    
    resultados = []
    for dominio, items in MAPEO_HOGAN.items():
        scores_others = []
        scores_self = []
        items_con_quorum = 0
        
        for n in items:
            col = next((c for c in df.columns if c.startswith(f"{n}.")), None)
            if col:
                # Cálculo de Others (Reputación)
                if others_data[col].count() >= MIN_OBS:
                    scores_others.append(others_data[col].mean())
                    items_con_quorum += 1
                
                # Cálculo de Self (Autopercepción) - Independiente de Others
                if not self_row.empty:
                    val_self = pd.to_numeric(self_row[col].iloc[0], errors='coerce')
                    if pd.notnull(val_self):
                        scores_self.append(val_self)

        cobertura = items_con_quorum / len(items)
        s_others = sum(scores_others)/len(scores_others) if scores_others else None
        s_self = sum(scores_self)/len(scores_self) if scores_self else None
        
        # Calidad basada en metodología 360
        calidad = "Sólido" if cobertura >= 0.8 else "Cautela" if cobertura >= 0.5 else "Insuficiente"
        
        resultados.append({
            "Categoría": dominio,
            "Autoevaluación (Self)": round(s_self, 2) if s_self else None,
            "Evaluaciones Recibidas (Others)": round(s_others, 2) if s_others else None,
            "Brecha (Gap)": round(s_self - s_others, 2) if (s_self and s_others) else None,
            "Cobertura": cobertura,
            "Confiabilidad": calidad
        })
    return pd.DataFrame(resultados)

def get_global_metrics(df):
    """Calcula el promedio de toda la organización."""
    nombres = df['Nombre de la persona Evaluada'].unique()
    todos_los_resultados = []
    for nombre in nombres:
        res = process_hogan_logic(df, nombre)
        todos_los_resultados.append(res)
    
    base_agregada = pd.concat(todos_los_resultados)
    # Promediar por categoría ignorando Nones
    global_df = base_agregada.groupby("Categoría").agg({
        "Autoevaluación (Self)": "mean",
        "Evaluaciones Recibidas (Others)": "mean"
    }).reset_index()
    
    return global_df.round(2)
