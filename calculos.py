import pandas as pd

def process_hogan_logic(df, nombre_evaluado, mapeo, min_obs=0): # min_obs ahora es opcional y 0
    nombre_target = str(nombre_evaluado).strip().lower()
    col_evaluado_str = "Nombre de la persona Evaluada"
    col_relacion_str = "Tu relación con el evaluado"
    
    # Filtro de nombre robusto
    df_persona = df[df[col_evaluado_str].astype(str).str.strip().str.lower() == nombre_target]
    
    # Separación
    es_auto = df_persona[col_relacion_str].astype(str).str.strip().str.lower() == 'autoevaluación'
    df_auto = df_persona[es_auto]
    df_otros = df_persona[~es_auto]
    
    resultados = []
    for dominio, items in mapeo.items():
        scores_otros = []
        scores_auto = []
        items_con_datos = 0
        
        for n in items:
            col_pregunta = next((c for c in df.columns if c.startswith(f"{n}.")), None)
            if col_pregunta:
                # Si hay al menos UNA respuesta de otros, la tomamos
                if not df_otros[col_pregunta].dropna().empty:
                    val_o = pd.to_numeric(df_otros[col_pregunta], errors='coerce').mean()
                    if pd.notnull(val_o):
                        scores_otros.append(val_o)
                        items_con_datos += 1
                
                # Autoevaluación
                if not df_auto.empty:
                    val_a = pd.to_numeric(df_auto[col_pregunta].iloc[0], errors='coerce')
                    if pd.notnull(val_a):
                        scores_auto.append(val_a)

        # Promedios (calculados si hay al menos 1 dato)
        p_otros = sum(scores_otros) / len(scores_otros) if scores_otros else 0.0
        p_auto = sum(scores_auto) / len(scores_auto) if scores_auto else 0.0
        
        resultados.append({
            "Categoría": dominio,
            "Autoevaluación": round(p_auto, 2),
            "Evaluación de los demás": round(p_otros, 2),
            "Brecha (Gap)": round(p_auto - p_otros, 2),
            "Cobertura": (items_con_datos / len(items)) if len(items) > 0 else 0
        })
        
    return pd.DataFrame(resultados)
