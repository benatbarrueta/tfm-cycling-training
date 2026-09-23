FEATURE_COLUMNS = (
    "tss_latest",
    "tss_previous",
    "tss_mean_4w",
)


def build_xy(
    rows: list[dict],
) -> tuple[list[list[float]], list[float]]:
    """Construye las entradas X y el objetivo y.
    
    Args:
        rows: Lista de diccionarios con los datos de entrenamiento/evaluación.
        
    Returns:
        X: Lista de listas con las características de entrada.
        y: Lista con los valores objetivo (next_week_tss).
"""
    X = []
    y = []

    for row in rows:
        X.append([float(row[col]) for col in FEATURE_COLUMNS])
        y.append(float(row["next_week_tss"]))

    return X, y