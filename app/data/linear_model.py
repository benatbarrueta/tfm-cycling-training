from sklearn.linear_model import LinearRegression

from collections import Counter

from app.data.ml_dataset import build_xy


def train_linear_model(
    train_rows: list[dict],
    *,
    balance_athletes: bool = False,
) -> LinearRegression:
    """Entrena una regresión con equilibrado opcional por atleta."""
    if not train_rows:
        raise ValueError("Se necesitan datos de entrenamiento.")

    X_train, y_train = build_xy(train_rows)
    model = LinearRegression()

    if balance_athletes:
        weights = build_athlete_weights(train_rows)
        model.fit(X_train, y_train, sample_weight=weights)
    else:
        model.fit(X_train, y_train)

    return model

def build_athlete_weights(rows: list[dict]) -> list[float]:
    """Asigna pesos para que cada atleta tenga el mismo peso total."""
    if not rows:
        raise ValueError("Se necesitan filas para calcular los pesos.")

    counts = Counter(row["athlete_id"] for row in rows)

    return [1 / counts[row["athlete_id"]] for row in rows]
