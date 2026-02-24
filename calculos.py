import pandas as pd

def process_hogan_logic(df, nombre_evaluado, mapeo, min_obs=0):
    nombre_target = str(nombre_evaluado).strip().lower()
    col_evaluado_str = "Nombre de la persona Evaluada"
    col_relacion_str = "Tu relación con el evaluado"
    
    df_persona = df[df[col_evaluado_str].astype(str).str.strip().str.lower() == nombre_target]
    
    # Definición de Roles según tu imagen
    roles = {
        "Autoevaluación": "autoevaluación",
        "Superior": "superior (yo soy su jefe)",
        "Subordinado": "subordinado (él/ella es mi jefe)",
        "Par": "par (colega del mismo nivel)"
    }
    
    resultados = []
    for dominio, items in mapeo.items():
        # Diccionario para guardar scores por rol
        rol_scores = {r: [] for r in roles.keys()}
        items_con_datos = 0
        
        for n in items:
            col_pregunta = next((c for c in df.columns if c.startswith(f"{n}.")), None)
            if col_pregunta:
                pregunta_tiene_datos = False
                for rol_label, valor_buscado in roles.items():
                    df_rol = df_persona[df_persona[col_relacion_str].astype(str).str.strip().str.lower() == valor_buscado]
                    
                    if not df_rol[col_pregunta].dropna().empty:
                        val = pd.to_numeric(df_rol[col_pregunta], errors='coerce').mean()
                        if pd.notnull(val):
                            rol_scores[rol_label].append(val)
                            pregunta_tiene_datos = True
                
                if pregunta_tiene_datos:
                    items_con_datos += 1

        # Calculamos promedios finales por rol
        res_row = {"Categoría": dominio}
        for rol_label in roles.keys():
            scores = rol_scores[rol_label]
            res_row[rol_label] = round(sum(scores) / len(scores), 2) if scores else 0.0
        
        cobertura = (items_con_datos / len(items)) if len(items) > 0 else 0
        res_row["Cobertura"] = cobertura
        res_row["Calidad"] = "Sólido" if cobertura >= 0.8 else "Cautela" if cobertura >= 0.5 else "Insuficiente"
        
        resultados.append(res_row)
        
    return pd.DataFrame(resultados)

def get_global_metrics(df, mapeo, min_obs=0):
    nombres = [n for n in df['Nombre de la persona Evaluada'].unique() if str(n).strip()]
    todos = [process_hogan_logic(df, n, mapeo, min_obs) for n in nombres]
    if not todos: return pd.DataFrame()
    df_global = pd.concat(todos)
    return df_global.groupby("Categoría").mean(numeric_only=True).reset_index().round(2)

def get_anonymous_feedback(df, nombre_evaluado):
    nombre_target = str(nombre_evaluado).strip().lower()
    col_evaluado_str = "Nombre de la persona Evaluada"
    
    # Filtramos la base principal por el líder exacto
    df_persona = df[df[col_evaluado_str].astype(str).str.strip().str.lower() == nombre_target]
    
    cols_cualitativas = [
        "¿Cuáles son las mayores fortalezas de esta persona?",
        "¿Cuáles son sus principales oportunidades de desarrollo?",
        "¿Hay alguna fortaleza que esta persona esté sobreutilizando?"
    ]
    
    # Extraemos estrictamente las columnas de texto
    cols_finales = [c for c in cols_cualitativas if c in df_persona.columns]
    
    # Retornamos los datos eliminando filas que estén totalmente vacías
    return df_persona[cols_finales].dropna(how='all')
