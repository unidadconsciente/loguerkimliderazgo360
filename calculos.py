def process_hogan_logic(df, nombre_lider):
    """Calcula promedios de ítems y dominios con validación de suficiencia."""
    df_persona = df[df['Nombre de la persona Evaluada'] == nombre_lider]
    self_data = df_persona[df_persona['Tu relación con el evaluado'] == 'Self']
    others_data = df_persona[df_persona['Tu relación con el evaluado'] != 'Self']
    
    rows = []
    for dominio, items in MAPEO_HOGAN.items():
        items_val_others = []
        cols_val = []
        
        # Validación de suficiencia por cada conducta
        for n in items:
            col = next((c for c in df.columns if c.startswith(f"{n}.")), None)
            if col and others_data[col].count() >= MIN_OBS:
                items_val_others.append(others_data[col].mean())
                cols_val.append(col)

        # Agregación por Dominio
        total = len(items)
        n_obs = len(items_val_others)
        cobertura = n_obs / total
        
        if n_obs > 0:
            score_others = sum(items_val_others) / n_obs
            # Alineación Self: solo promedia lo que Others pudo observar
            score_self = self_data[cols_val].mean(axis=1).iloc[0] if not self_data.empty and cols_val else None
            
            rows.append({
                "Dominio": dominio,
                "Self": score_self,
                "Others": round(score_others, 2),
                "Gap": round(score_self - score_others, 2) if score_self is not None else None,
                "Cobertura": cobertura,
                "Calidad": "Sólido" if cobertura >= 0.8 else "Interpretación Cautelosa" if cobertura >= 0.5 else "Baja"
            })
        else:
            rows.append({"Dominio": dominio, "Self": None, "Others": None, "Cobertura": 0, "Calidad": "Insuficiente"})
            
    return pd.DataFrame(rows)
