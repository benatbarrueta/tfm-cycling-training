import argparse
import csv
import json
import math

from pathlib import Path

from app.data.response_evaluation import (
    FEATURE_COLUMNS,
    train_balanced_response_linear_model,
)


def train_response_model_artifact(
    rows: list[dict],
) -> dict:
    """Entrena la regresión equilibrada y crea un artefacto serializable."""
    if not rows:
        raise ValueError(
            "Se necesitan filas para entrenar el modelo."
        )

    model = train_balanced_response_linear_model(
        rows
    )

    intercept = float(model.intercept_)
    coefficients = [
        float(value)
        for value in model.coef_
    ]

    if (
        not math.isfinite(intercept)
        or any(
            not math.isfinite(value)
            for value in coefficients
        )
    ):
        raise ValueError(
            "El modelo contiene parámetros no finitos."
        )

    athlete_ids = {
        row["athlete_id"]
        for row in rows
    }

    feature_ranges = {
        column: {
            "min": min(
                float(row[column])
                for row in rows
            ),
            "max": max(
                float(row[column])
                for row in rows
            ),
        }
        for column in FEATURE_COLUMNS
    }

    return {
        "model_type": "balanced_linear_regression",
        "target": "calculated_aerobic_decoupling",
        "feature_columns": list(FEATURE_COLUMNS),
        "intercept": intercept,
        "coefficients": coefficients,
        "feature_ranges": feature_ranges,
        "training_rows": len(rows),
        "training_athletes": len(athlete_ids),
        "athlete_weighting": "equal_total_weight",
    }

def predict_response_from_artifact(
    artifact: dict,
    features: dict,
) -> float:
    """Predice el desacoplamiento usando un artefacto lineal."""
    feature_columns = artifact["feature_columns"]
    coefficients = artifact["coefficients"]

    if len(feature_columns) != len(coefficients):
        raise ValueError(
            "El número de variables y coeficientes no coincide."
        )

    try:
        values = [
            float(features[column])
            for column in feature_columns
        ]
    except KeyError as error:
        raise ValueError(
            f"Falta la variable {error.args[0]}."
        ) from error

    if any(
        not math.isfinite(value)
        for value in values
    ):
        raise ValueError(
            "Las variables deben contener valores finitos."
        )

    prediction = float(artifact["intercept"])

    prediction += sum(
        coefficient * value
        for coefficient, value in zip(
            coefficients,
            values,
        )
    )

    return prediction

def save_response_model_artifact(
    artifact: dict,
    output: str | Path,
) -> None:
    """Guarda el artefacto del modelo en formato JSON."""
    output = Path(output)
    output.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    output.write_text(
        json.dumps(
            artifact,
            indent=2,
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )

def load_response_model_artifact(
    path: str | Path,
) -> dict:
    """Carga un artefacto de regresión desde JSON."""
    with Path(path).open(
        encoding="utf-8"
    ) as file:
        return json.load(file)

def find_outside_training_range_features(
    artifact: dict,
    features: dict,
) -> list[str]:
    """Devuelve las variables fuera del rango observado al entrenar."""
    feature_ranges = artifact.get(
        "feature_ranges",
        {}
    )

    outside_features = []

    for column in artifact["feature_columns"]:
        limits = feature_ranges.get(column)

        if limits is None:
            continue

        value = float(
            features[column]
        )

        if (
            value < float(limits["min"])
            or value > float(limits["max"])
        ):
            outside_features.append(
                column
            )

    return outside_features

def main() -> None:
    """Entrena y guarda el modelo final de respuesta."""
    parser = argparse.ArgumentParser(
        description=(
            "Entrena la regresión equilibrada final "
            "de respuesta aeróbica."
        )
    )

    parser.add_argument(
        "input",
        type=Path,
        help="Dataset de respuesta en CSV.",
    )
    parser.add_argument(
        "--output",
        type=Path,
        required=True,
        help="Ruta del artefacto JSON.",
    )

    args = parser.parse_args()

    with args.input.open(
        encoding="utf-8",
        newline="",
    ) as file:
        rows = list(
            csv.DictReader(file)
        )

    artifact = train_response_model_artifact(
        rows
    )

    save_response_model_artifact(
        artifact,
        args.output,
    )

    print(
        f"Modelo guardado en: {args.output}"
    )
    print(
        f"Filas de entrenamiento: "
        f"{artifact['training_rows']}"
    )
    print(
        f"Atletas: "
        f"{artifact['training_athletes']}"
    )

if __name__ == "__main__":
    main()