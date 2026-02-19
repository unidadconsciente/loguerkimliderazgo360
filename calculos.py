import pandas as pd

def process_hogan_logic(df, nombre_evaluado, mapeo, min_obs=0):
    nombre_target = str(nombre_evaluado).strip().lower()
    col_evaluado_str = "Nombre de la persona Evaluada"
    col_relacion_str = "Tu relación con el evaluado"
    
    df_persona = df[df[col_evaluado_str].astype(str).str.strip().str.lower() == nombre_target]
    
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
                if not df_otros[col_pregunta].dropna().empty:
                    val_o = pd.to_numeric(df_otros[col_pregunta], errors='coerce').mean()
                    if pd.notnull(val_o):
                        scores_otros.append(val_o)
                        items_con_datos += 1
                
                if not df_auto.empty:
                    val_a = pd.to_numeric(df_auto[col_pregunta].iloc[0], errors='coerce')
                    if pd.notnull(val_a):
                        scores_auto.append(val_a)

        p_otros = sum(scores_otros) / len(scores_otros) if scores_otros else 0.0
        p_auto = sum(scores_auto) / len(scores_auto) if scores_auto else 0.0
        cobertura = (items_con_datos / len(items)) if len(items) > 0 else 0
        
        # Lógica de Calidad solicitada
        if cobertura >= 0.8:
            calidad_txt = "Sólido"
        elif cobertura >= 0.5:
            calidad_txt = "Cautela"
        else:
            calidad_txt = "Insuficiente"
        
        resultados.append({
            "Categoría": dominio,
            "Autoevaluación": round(p_auto, 2),
            "Evaluación de los demás": round(p_otros, 2),
            "Brecha (Gap)": round(p_auto - p_otros, 2),
            "Cobertura": cobertura,
            "Calidad": calidad_txt
        })
        
    return pd.DataFrame(resultados)

def get_global_metrics(df, mapeo, min_obs=0):
    nombres = [n for n in df['Nombre de la persona Evaluada'].unique() if str(n).strip()]
    todos = [process_hogan_logic(df, n, mapeo, min_obs) for n in nombres]
    if not todos: return pd.DataFrame()
    df_global = pd.concat(todos)
    return df_global.groupby("Categoría").agg({
        "Autoevaluación": "mean",
        "Evaluación de los demás": "mean"
    }).reset_index().round(2)
