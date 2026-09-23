import argparse
import csv
from pathlib import Path

from app.data.linear_model import train_linear_model
from app.data.ml_dataset import build_xy

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

def build_athlete_folds(
    train_rows: list[dict],
) -> list[tuple[list[dict], list[dict]]]:
    """Crea particiones dejando un atleta fuera en cada iteración."""
    athlete_ids = sorted({
        row["athlete_id"] for row in train_rows
    })

    if len(athlete_ids) < 2:
        raise ValueError("Se necesitan al menos dos atletas.")

    folds = []

    for athlete_id in athlete_ids:
        train_fold, test_fold = split_by_athlete(train_rows, {athlete_id})
        folds.append((train_fold, test_fold))

    return folds

def cross_validate_by_athlete(train_rows: list[dict]) -> list[dict]:
    """Compara los tres métodos dejando un atleta fuera cada vez."""
    results = []

    for train_fold, validation_fold in build_athlete_folds(train_rows):
        model = train_linear_model(train_fold)

        X_validation, y_validation = build_xy(validation_fold)
        predictions = model.predict(X_validation)

        balanced_model = train_linear_model(
            train_fold,
            balance_athletes=True,
        )

        balanced_predictions = balanced_model.predict(X_validation)

        athlete_id = validation_fold[0]["athlete_id"]

        if athlete_id == "02a72bf5-d3cf-4502-ac7f-1828abb367ae":
            print("\nDetalle del atleta con dos filas:")

            for row, prediction in zip(validation_fold, predictions):
                print(
                    f"Semana objetivo: {row['target_week']} | "
                    f"Último TSS: {float(row['tss_latest']):.2f} | "
                    f"Media 4 semanas: {float(row['tss_mean_4w']):.2f} | "
                    f"TSS real: {float(row['next_week_tss']):.2f} | "
                    f"Predicción: {prediction:.2f}"
                )

            print(f"Intercepto: {model.intercept_:.2f}")
            print(f"Coeficientes: {model.coef_}")

            training_means = sorted(
                float(row["tss_mean_4w"])
                for row in train_fold
            )

            low_load_count = sum(
                value <= 50
                for value in training_means
            )

            print(
                "Rango de medias de entrenamiento: "
                f"{training_means[0]:.2f}–"
                f"{training_means[-1]:.2f} TSS"
            )
            print(
                "Filas de entrenamiento con media <= 50 TSS: "
                f"{low_load_count}/{len(training_means)}"
            )

        outside_count = sum(
            is_outside_training_mean_range(train_fold, row)
            for row in validation_fold
        )

        results.append({
            "athlete_id": validation_fold[0]["athlete_id"],
            "n_rows": len(validation_fold),
            "persistence_mae": evaluate_persistence(validation_fold),
            "rolling_mean_mae": evaluate_rolling_mean(validation_fold),
            "linear_mae": calculate_mae(y_validation, predictions.tolist()),
            "outside_range_count": outside_count,
                        "balanced_linear_mae": calculate_mae(
                y_validation,
                balanced_predictions.tolist(),
            ),
        })

    return results

def is_outside_training_mean_range(
    train_rows: list[dict],
    row: dict,
) -> bool:
    """Indica si la media de carga está fuera del rango de entrenamiento."""
    if not train_rows:
        raise ValueError("Se necesitan datos de entrenamiento.")

    training_means = [
        float(item["tss_mean_4w"])
        for item in train_rows
    ]

    value = float(row["tss_mean_4w"])

    return value < min(training_means) or value > max(training_means)

def save_cv_results(results: list[dict], output: Path) -> None:
    """Guarda los resultados de validación por atleta en CSV."""
    if not results:
        raise ValueError("No hay resultados que guardar.")

    output.parent.mkdir(parents=True, exist_ok=True)

    with output.open("w", encoding="utf-8", newline="") as file:
        writer = csv.DictWriter(
            file,
            fieldnames=list(results[0]),
        )

        writer.writeheader()
        writer.writerows(results)

def main():
    parser = argparse.ArgumentParser(
        description="Compara persistencia, media de cuatro semanas y regresión lineal."
    )
    parser.add_argument("input", type=Path)
    parser.add_argument("--test-athletes", nargs="+", required=True)
    parser.add_argument(
        "--cv-output",
        type=Path,
        default=Path("data/processed/evaluation/linear_baseline_cv.csv"),
        help="Ruta del CSV con los resultados de validación interna.",
    )
    parser.add_argument(
        "--cv-only",
        action="store_true",
        help="Ejecuta solo la validación interna.",
    )
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

    cv_results = cross_validate_by_athlete(train_rows)

    if args.cv_output is not None:
        save_cv_results(cv_results, args.cv_output)
        print(f"Validación guardada en: {args.cv_output}")

    print("\nValidación interna por atleta:")

    for result in cv_results:
        print(
            f"{result['athlete_id']} "
            f"({result['n_rows']} filas): "
            f"persistencia={result['persistence_mae']:.2f}, "
            f"media 4 semanas={result['rolling_mean_mae']:.2f}, "
            f"regresión={result['linear_mae']:.2f}, "
            f"regresión equilibrada="
            f"{result['balanced_linear_mae']:.2f} TSS, "
            f"fuera de rango="
            f"{result['outside_range_count']}/{result['n_rows']}"
        )

    print("\nMAE medio por atleta en validación:")

    for metric in (
        "persistence_mae",
        "rolling_mean_mae",
        "linear_mae",
        "balanced_linear_mae",
    ):
        mean_mae = sum(
            result[metric] for result in cv_results
        ) / len(cv_results)

        print(f"{metric}: {mean_mae:.2f} TSS")


    if args.cv_only:
        return

    model = train_linear_model(train_rows)

    X_test, y_test = build_xy(test_rows)
    predictions = model.predict(X_test)

    linear_mae = calculate_mae(y_test, predictions.tolist())

    print(f"MAE regresión lineal: {linear_mae:.2f} TSS")

    print(f"Filas de entrenamiento: {len(train_rows)}")

    print(f"Filas de evaluación: {len(test_rows)}")

    print(
        f"MAE persistencia: "
        f"{evaluate_persistence(test_rows):.2f} TSS"
    )
    
    print(
        f"MAE media de 4 semanas: "
        f"{evaluate_rolling_mean(test_rows):.2f} TSS"
    )

    persistence_maes = []
    rolling_maes = []
    linear_maes = []

    for athlete_id in sorted({row["athlete_id"] for row in test_rows}):
        athlete_rows = [
            row for row in test_rows
            if row["athlete_id"] == athlete_id
        ]

        persistence_mae = evaluate_persistence(athlete_rows)
        rolling_mae = evaluate_rolling_mean(athlete_rows)
        X_athlete, y_athlete = build_xy(athlete_rows)
        athlete_predictions = model.predict(X_athlete)

        athlete_linear_mae = calculate_mae(
            y_athlete,
            athlete_predictions.tolist(),
        )        

        persistence_maes.append(persistence_mae)
        rolling_maes.append(rolling_mae)
        linear_maes.append(athlete_linear_mae)

        print(
            f"Atleta {athlete_id}: "
            f"persistencia={persistence_mae:.2f}, "
            f"media 4 semanas={rolling_mae:.2f} TSS, "
            f"regresión lineal={athlete_linear_mae:.2f} TSS"
        )

    print(
        "MAE medio por atleta — regresión lineal: "
        f"{sum(linear_maes) / len(linear_maes):.2f} TSS"
    )

    print(
        "MAE medio por atleta — persistencia: "
        f"{sum(persistence_maes) / len(persistence_maes):.2f} TSS"
    )
    print(
        "MAE medio por atleta — media 4 semanas: "
        f"{sum(rolling_maes) / len(rolling_maes):.2f} TSS"
    )


if __name__ == "__main__":
    main()