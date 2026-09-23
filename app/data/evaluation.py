import argparse
import csv
from pathlib import Path

def calculate_mae(
    actual: list[float],
    predicted: list[float],
) -> float:
    """Calcula el error absoluto medio."""
    if not actual:
        raise ValueError("Se requiere al menos una observación.")

    if len(actual) != len(predicted):
        raise ValueError("Las listas deben tener la misma longitud.")
    
    errors = [abs(a - p) for a, p in zip(actual, predicted)]
    return sum(errors) / len(errors)

def split_by_athlete(
    rows: list[dict],
    test_athlete_ids: set[str],
) -> tuple[list[dict], list[dict]]:
    """Separa entrenamiento y evaluación por identificador de atleta."""
    available_ids = {row["athlete_id"] for row in rows}

    if not test_athlete_ids:
        raise ValueError("Selecciona al menos un atleta para evaluación.")

    if not test_athlete_ids.issubset(available_ids):
        raise ValueError("Hay atletas de evaluación que no existen.")

    train_rows = []
    test_rows = []

    for row in rows:
        if row["athlete_id"] in test_athlete_ids:
            test_rows.append(row)
        else:
            train_rows.append(row)

    if not train_rows:
        raise ValueError("Debe quedar algún atleta para entrenamiento.")

    return train_rows, test_rows

def evaluate_persistence(rows: list[dict]) -> float:
    """Evalúa la predicción: próxima carga = última carga observada."""
    actual = [
        row["next_week_tss"] for row in rows
    ]

    predicted = [
        row["tss_latest"] for row in rows
    ]

    return calculate_mae(actual, predicted)

def evaluate_rolling_mean(rows: list[dict]) -> float:
    """Evalúa la media de las cuatro semanas como predicción."""
    actual = [
        row["next_week_tss"] for row in rows
    ]

    predicted = [
        row["tss_mean_4w"] for row in rows
    ]

    return calculate_mae(actual, predicted)

def main():
    parser = argparse.ArgumentParser(
        description="Evalúa la predicción de persistencia por atleta."
    )
    parser.add_argument("input", type=Path)
    parser.add_argument("--test-athletes", nargs="+", required=True)
    args = parser.parse_args()

    with args.input.open(encoding="utf-8", newline="") as file:
        rows = list(csv.DictReader(file))

    for row in rows:
        row["tss_latest"] = float(row["tss_latest"])
        row["next_week_tss"] = float(row["next_week_tss"])
        row["tss_mean_4w"] = float(row["tss_mean_4w"])

    train_rows, test_rows = split_by_athlete(
        rows,
        set(args.test_athletes),
    )

    print(f"Filas de entrenamiento: {len(train_rows)}")
    print(f"Filas de evaluación: {len(test_rows)}")
    print(f"MAE global: {evaluate_persistence(test_rows):.2f} TSS")
    print(
    f"MAE media de 4 semanas: "
    f"{evaluate_rolling_mean(test_rows):.2f} TSS"
)

    athlete_maes = []

    for athlete_id in sorted({row["athlete_id"] for row in test_rows}):
        athlete_rows = [
            row for row in test_rows
            if row["athlete_id"] == athlete_id
        ]
        mae = evaluate_persistence(athlete_rows)
        athlete_maes.append(mae)
        print(f"Atleta {athlete_id}: {mae:.2f} TSS")

    print(
        f"MAE medio por atleta: "
        f"{sum(athlete_maes) / len(athlete_maes):.2f} TSS"
    )


if __name__ == "__main__":
    main()