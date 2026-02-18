import pandas as pd

def process_hogan_logic(df, nombre_evaluado, mapeo, min_obs):
    # 1. Filtramos todo lo relacionado a la persona
    df_persona = df[df['Nombre de la persona Evaluada'] == nombre_evaluado]
    
    # 2. Identificamos la columna de relación (Posición 7, índice 6)
    col_relacion = df.columns[6]
    
    # 3. SEPARACIÓN REAL: Autoevaluación vs Otros
    # Buscamos específicamente la palabra que usas en el Sheet
    es_auto = df_persona[col_relacion].astype(str).str.strip().str.lower() == 'autoevaluación'
    
    df_autoevaluacion = df_persona[es_auto]
    df_otros = df_persona[~es_auto] # Todo lo que NO sea Autoevaluación
    
    resultados = []
    
    for dominio, items in mapeo.items():
        scores_otros = []
        scores_auto = []
        items_con_quorum = 0
        
        for n in items:
            col_pregunta = next((c for c in df.columns if c.startswith(f"{n}.")), None)
            
            if col_pregunta:
                # Cálculo para Otros (Barra Naranja)
                if df_otros[col_pregunta].count() >= min_obs:
                    val_otros = pd.to_numeric(df_otros[col_pregunta], errors='coerce').mean()
                    if pd.notnull(val_others):
                        scores_otros.append(val_others)
                        items_con_quorum += 1
                
                # Cálculo para Autoevaluación (Barra Azul)
                if not df_autoevaluacion.empty:
                    val_auto = pd.to_numeric(df_autoevaluacion[col_pregunta].iloc[0], errors='coerce')
                    if pd.notnull(val_auto):
                        scores_auto.append(val_auto)

        cobertura = items_con_quorum / len(items)
        promedio_otros = sum(scores_otros) / len(scores_otros) if scores_otros else None
        promedio_auto = sum(scores_auto) / len(scores_auto) if scores_auto else None
        
        calidad = "Sólido" if cobertura >= 0.8 else "Cautela" if cobertura >= 0.5 else "Insuficiente"
        
        resultados.append({
            "Categoría": dominio,
            "Autoevaluación": round(promedio_auto, 2) if promedio_auto else None,
            "Evaluación de los demás": round(promedio_otros, 2) if promedio_otros else None,
            "Brecha (Gap)": round(promedio_auto - promedio_otros, 2) if (promedio_auto and promedio_otros) else None,
            "Cobertura": cobertura,
            "Confiabilidad": calidad
        })
        
    return pd.DataFrame(resultados)

def get_global_metrics(df, mapeo, min_obs):
    nombres = df['Nombre de la persona Evaluada'].unique()
    todos = []
    for n in nombres:
        todos.append(process_hogan_logic(df, n, mapeo, min_obs))
    
    if not todos: return pd.DataFrame()
    
    df_global = pd.concat(todos)
    return df_global.groupby("Categoría").agg({
        "Autoevaluación": "mean",
        "Evaluación de los demás": "mean"
    }).reset_index().round(2)
