import pandas as pd

def process_hogan_logic(df, nombre_evaluado, mapeo, min_obs=0):
    # 1. Normalización de identidad
    nombre_target = str(nombre_evaluado).strip().lower()
    col_evaluado_str = "Nombre de la persona Evaluada"
    col_relacion_str = "Tu relación con el evaluado"
    
    # Filtro de nombre robusto para traer todo lo relacionado a la persona
    df_persona = df[df[col_evaluado_str].astype(str).str.strip().str.lower() == nombre_target]
    
    # 2. Separación: Autoevaluación vs El resto (Evaluación de los demás)
    es_auto = df_persona[col_relacion_str].astype(str).str.strip().str.lower() == 'autoevaluación'
    df_auto = df_persona[es_auto]
    df_otros = df_persona[~es_auto]
    
    resultados = []
    
    for dominio, items in mapeo.items():
        scores_otros = []
        scores_auto = []
        items_con_datos = 0
        
        for n in items:
            # Identificar columna por número (ej: "1. ")
            col_pregunta = next((c for c in df.columns if c.startswith(f"{n}.")), None)
            
            if col_pregunta:
                # Otros: Si hay al menos un dato, lo promediamos
                if not df_otros[col_pregunta].dropna().empty:
                    val_o = pd.to_numeric(df_otros[col_pregunta], errors='coerce').mean()
                    if pd.notnull(val_o):
                        scores_otros.append(val_o)
                        items_con_datos += 1
                
                # Auto: Tomamos el valor de su fila de autoevaluación
                if not df_auto.empty:
                    val_a = pd.to_numeric(df_auto[col_pregunta].iloc[0], errors='coerce')
                    if pd.notnull(val_a):
                        scores_auto.append(val_a)

        # Promedios finales (0.0 si no hay datos para evitar errores de formateo)
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

def get_global_metrics(df, mapeo, min_obs=0):
    nombres = [n for n in df['Nombre de la persona Evaluada'].unique() if str(n).strip()]
    todos = []
    for n in nombres:
        res = process_hogan_logic(df, n, mapeo, min_obs)
        if not res.empty:
            todos.append(res)
    
    if not todos:
        return pd.DataFrame()
    
    df_global = pd.concat(todos)
    return df_global.groupby("Categoría").agg({
        "Autoevaluación": "mean",
        "Evaluación de los demás": "mean"
    }).reset_index().round(2)
