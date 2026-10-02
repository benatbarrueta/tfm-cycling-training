import argparse
import csv

from pathlib import Path
from statistics import median

from sklearn.linear_model import (
    LinearRegression,
    Ridge,
)
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler
from sklearn.ensemble import RandomForestRegressor

from app.data.linear_model import (
    build_athlete_weights,
)

from app.data.evaluation import (
    build_athlete_folds,
    calculate_mae,
    split_by_athlete,
)

FEATURE_COLUMNS = (
    "session_duration_minutes",
    "session_intensity_factor",
    "session_tss",
    "previous_7d_tss",
    "previous_7d_activity_count",
    "previous_28d_tss",
    "previous_28d_activity_count",
    "acute_chronic_load_ratio",
    "session_to_chronic_load_ratio",
    "previous_response_median",
    "previous_response_count",
)

def evaluate_median_baseline(
    train_rows: list[dict],
    test_rows: list[dict],
) -> float:
    """Evalúa la predicción constante basada en la mediana de entrenamiento."""
    if not train_rows:
        raise ValueError(
            "Se necesitan filas de entrenamiento."
        )

    if not test_rows:
        raise ValueError(
            "Se necesitan filas de evaluación."
        )

    training_targets = [
        float(row["target_aerobic_decoupling"])
        for row in train_rows
    ]

    actual = [
        float(row["target_aerobic_decoupling"])
        for row in test_rows
    ]

    baseline_prediction = median(training_targets)

    predicted = [
        baseline_prediction
        for _ in test_rows
    ]

    return calculate_mae(
        actual,
        predicted,
    )

def build_response_xy(
    rows: list[dict],
) -> tuple[list[list[float]], list[float]]:
    """Construye las entradas y el objetivo del modelo de respuesta."""
    X = [
        [
            float(row[column])
            for column in FEATURE_COLUMNS
        ]
        for row in rows
    ]

    y = [
        float(row["target_aerobic_decoupling"])
        for row in rows
    ]

    return X, y

def train_response_linear_model(
    train_rows: list[dict],
) -> LinearRegression:
    """Entrena una regresión lineal para predecir desacoplamiento."""
    if not train_rows:
        raise ValueError(
            "Se necesitan filas de entrenamiento."
        )

    X_train, y_train = build_response_xy(
        train_rows
    )

    model = LinearRegression()
    model.fit(X_train, y_train)

    return model

def evaluate_response_linear_model(
    model: LinearRegression,
    test_rows: list[dict],
) -> float:
    """Calcula el MAE de la regresión lineal."""
    if not test_rows:
        raise ValueError(
            "Se necesitan filas de evaluación."
        )

    X_test, y_test = build_response_xy(
        test_rows
    )

    predictions = model.predict(X_test)

    return calculate_mae(
        y_test,
        predictions.tolist(),
    )

def cross_validate_response_by_athlete(
    train_rows: list[dict],
) -> list[dict]:
    """Compara mediana y regresión dejando fuera un atleta cada vez."""
    results = []

    for train_fold, validation_fold in build_athlete_folds(
        train_rows
    ):
        athlete_id = validation_fold[0]["athlete_id"]

        baseline_mae = evaluate_median_baseline(
            train_fold,
            validation_fold,
        )

        model = train_response_linear_model(
            train_fold
        )

        linear_mae = evaluate_response_linear_model(
            model,
            validation_fold,
        )

        balanced_model = (
            train_balanced_response_linear_model(
                train_fold
            )
        )

        balanced_linear_mae = (
            evaluate_response_linear_model(
                balanced_model,
                validation_fold,
            )
        )

        personal_median_mae = (
            evaluate_personal_median_baseline(
                validation_fold
            )
        )

        results.append({
            "athlete_id": athlete_id,
            "n_rows": len(validation_fold),
            "median_mae": baseline_mae,
            "linear_mae": linear_mae,
            "balanced_linear_mae": balanced_linear_mae,
            "personal_median_mae": personal_median_mae,
        })

    return results

def train_response_ridge_model(
    train_rows: list[dict],
    *,
    alpha: float = 1.0,
):
    """Entrena una regresión Ridge con variables estandarizadas."""
    if not train_rows:
        raise ValueError(
            "Se necesitan filas de entrenamiento."
        )

    if alpha <= 0:
        raise ValueError(
            "Alpha debe ser mayor que cero."
        )

    X_train, y_train = build_response_xy(
        train_rows
    )

    model = make_pipeline(
        StandardScaler(),
        Ridge(alpha=alpha),
    )

    model.fit(
        X_train,
        y_train,
    )

    return model

def evaluate_response_ridge_model(
    model,
    test_rows: list[dict],
) -> float:
    """Calcula el MAE de una regresión Ridge."""
    if not test_rows:
        raise ValueError(
            "Se necesitan filas de evaluación."
        )

    X_test, y_test = build_response_xy(
        test_rows
    )

    predictions = model.predict(X_test)

    return calculate_mae(
        y_test,
        predictions.tolist(),
    )

def cross_validate_ridge_alphas(
    train_rows: list[dict],
    alphas: tuple[float, ...],
) -> list[dict]:
    """Evalúa varios valores de alpha dejando fuera un atleta."""
    if not alphas:
        raise ValueError(
            "Se requiere al menos un valor de alpha."
        )

    folds = build_athlete_folds(
        train_rows
    )

    results = []

    for alpha in alphas:
        fold_maes = []

        for train_fold, validation_fold in folds:
            model = train_response_ridge_model(
                train_fold,
                alpha=alpha,
            )

            mae = evaluate_response_ridge_model(
                model,
                validation_fold,
            )

            fold_maes.append(mae)

        results.append({
            "alpha": alpha,
            "mean_athlete_mae": (
                sum(fold_maes) / len(fold_maes)
            ),
            "fold_count": len(fold_maes),
        })

    return results

def train_response_random_forest(
    train_rows: list[dict],
    *,
    n_estimators: int = 300,
    max_depth: int | None = None,
    min_samples_leaf: int = 5,
) -> RandomForestRegressor:
    """Entrena un bosque aleatorio para predecir desacoplamiento."""
    if not train_rows:
        raise ValueError(
            "Se necesitan filas de entrenamiento."
        )

    if n_estimators <= 0:
        raise ValueError(
            "El número de árboles debe ser mayor que cero."
        )

    if min_samples_leaf <= 0:
        raise ValueError(
            "El mínimo de muestras por hoja debe ser positivo."
        )

    X_train, y_train = build_response_xy(
        train_rows
    )

    model = RandomForestRegressor(
        n_estimators=n_estimators,
        max_depth=max_depth,
        min_samples_leaf=min_samples_leaf,
        random_state=42,
        n_jobs=-1,
    )

    model.fit(
        X_train,
        y_train,
    )

    return model

def evaluate_response_random_forest(
    model: RandomForestRegressor,
    test_rows: list[dict],
) -> float:
    """Calcula el MAE del bosque aleatorio."""
    if not test_rows:
        raise ValueError(
            "Se necesitan filas de evaluación."
        )

    X_test, y_test = build_response_xy(
        test_rows
    )

    predictions = model.predict(X_test)

    return calculate_mae(
        y_test,
        predictions.tolist(),
    )

def cross_validate_random_forest_configs(
    train_rows: list[dict],
    configs: tuple[tuple[int | None, int], ...],
    *,
    n_estimators: int = 300,
) -> list[dict]:
    """Evalúa configuraciones del bosque dejando fuera un atleta."""
    if not configs:
        raise ValueError(
            "Se requiere al menos una configuración."
        )

    folds = build_athlete_folds(
        train_rows
    )

    results = []

    for max_depth, min_samples_leaf in configs:
        fold_maes = []

        for train_fold, validation_fold in folds:
            model = train_response_random_forest(
                train_fold,
                n_estimators=n_estimators,
                max_depth=max_depth,
                min_samples_leaf=min_samples_leaf,
            )

            mae = evaluate_response_random_forest(
                model,
                validation_fold,
            )

            fold_maes.append(mae)

        results.append({
            "max_depth": max_depth,
            "min_samples_leaf": min_samples_leaf,
            "mean_athlete_mae": (
                sum(fold_maes) / len(fold_maes)
            ),
            "fold_count": len(fold_maes),
        })

    return results

def train_balanced_response_linear_model(
    train_rows: list[dict],
) -> LinearRegression:
    """Entrena una regresión dando el mismo peso total a cada atleta."""
    if not train_rows:
        raise ValueError(
            "Se necesitan filas de entrenamiento."
        )

    X_train, y_train = build_response_xy(
        train_rows
    )

    sample_weights = build_athlete_weights(
        train_rows
    )

    model = LinearRegression()

    model.fit(
        X_train,
        y_train,
        sample_weight=sample_weights,
    )

    return model

def evaluate_personal_median_baseline(
    rows: list[dict],
) -> float:
    """Evalúa la mediana histórica propia de cada actividad."""
    if not rows:
        raise ValueError(
            "Se necesitan filas de evaluación."
        )

    actual = [
        float(row["target_aerobic_decoupling"])
        for row in rows
    ]

    predicted = [
        float(row["previous_response_median"])
        for row in rows
    ]

    return calculate_mae(
        actual,
        predicted,
    )

def cross_validate_fixed_models_by_athlete(
    rows: list[dict],
    *,
    ridge_alpha: float = 1.0,
    forest_max_depth: int | None = None,
    forest_min_samples_leaf: int = 20,
    forest_n_estimators: int = 300,
) -> list[dict]:
    """Evalúa modelos fijados dejando fuera un atleta cada vez."""
    results = []

    for train_fold, validation_fold in build_athlete_folds(
        rows
    ):
        athlete_id = validation_fold[0]["athlete_id"]

        global_median_mae = evaluate_median_baseline(
            train_fold,
            validation_fold,
        )

        personal_median_mae = (
            evaluate_personal_median_baseline(
                validation_fold
            )
        )

        linear_model = train_response_linear_model(
            train_fold
        )
        linear_mae = evaluate_response_linear_model(
            linear_model,
            validation_fold,
        )

        balanced_model = (
            train_balanced_response_linear_model(
                train_fold
            )
        )
        balanced_linear_mae = (
            evaluate_response_linear_model(
                balanced_model,
                validation_fold,
            )
        )

        ridge_model = train_response_ridge_model(
            train_fold,
            alpha=ridge_alpha,
        )
        ridge_mae = evaluate_response_ridge_model(
            ridge_model,
            validation_fold,
        )

        forest_model = train_response_random_forest(
            train_fold,
            n_estimators=forest_n_estimators,
            max_depth=forest_max_depth,
            min_samples_leaf=forest_min_samples_leaf,
        )
        forest_mae = evaluate_response_random_forest(
            forest_model,
            validation_fold,
        )

        results.append({
            "athlete_id": athlete_id,
            "n_rows": len(validation_fold),
            "global_median_mae": global_median_mae,
            "personal_median_mae": personal_median_mae,
            "linear_mae": linear_mae,
            "balanced_linear_mae": balanced_linear_mae,
            "ridge_mae": ridge_mae,
            "forest_mae": forest_mae,
        })

    return results

def main():
    parser = argparse.ArgumentParser(
        description=(
            "Evalúa la predicción de desacoplamiento "
            "sobre atletas no vistos."
        )
    )

    parser.add_argument(
        "input",
        type=Path,
        help="Ruta al dataset de respuesta.",
    )

    parser.add_argument(
        "--test-athletes",
        nargs="+",
        help=(
            "Identificadores de atletas reservados "
            "para evaluación."
        ),
    )

    parser.add_argument(
        "--full-cv",
        action="store_true",
        help=(
            "Evalúa configuraciones fijadas dejando fuera "
            "cada atleta una vez."
        ),
    )

    args = parser.parse_args()

    with args.input.open(
        encoding="utf-8",
        newline="",
    ) as file:
        rows = list(csv.DictReader(file))

    if args.full_cv:
        full_cv_results = (
            cross_validate_fixed_models_by_athlete(
                rows,
                ridge_alpha=1.0,
                forest_max_depth=None,
                forest_min_samples_leaf=20,
            )
        )

        print(
            "Evaluación leave-one-athlete-out "
            "sobre los diez atletas:"
        )

        for result in full_cv_results:
            print(
                f"{result['athlete_id']} "
                f"({result['n_rows']} filas): "
                f"mediana global="
                f"{result['global_median_mae']:.2f}, "
                f"mediana personal="
                f"{result['personal_median_mae']:.2f}, "
                f"lineal={result['linear_mae']:.2f}, "
                f"lineal equilibrada="
                f"{result['balanced_linear_mae']:.2f}, "
                f"Ridge={result['ridge_mae']:.2f}, "
                f"Random Forest="
                f"{result['forest_mae']:.2f}"
            )

        print(
            "\nMAE medio por atleta:"
        )

        metrics = (
            ("Mediana global", "global_median_mae"),
            ("Mediana personal", "personal_median_mae"),
            ("Regresión lineal", "linear_mae"),
            (
                "Regresión equilibrada",
                "balanced_linear_mae",
            ),
            ("Ridge", "ridge_mae"),
            ("Random Forest", "forest_mae"),
        )

        for label, key in metrics:
            mean_mae = sum(
                result[key]
                for result in full_cv_results
            ) / len(full_cv_results)

            print(
                f"{label}: {mean_mae:.2f} "
                "puntos de desacoplamiento"
            )

        return

    train_rows, test_rows = split_by_athlete(
        rows,
        set(args.test_athletes),
    )

    cv_results = cross_validate_response_by_athlete(
        train_rows
    )

    print("Validación interna por atleta:")

    for result in cv_results:
        print(
            f"{result['athlete_id']} "
            f"({result['n_rows']} filas): "
            f"mediana={result['median_mae']:.2f}, "
            f"regresión={result['linear_mae']:.2f}"
            f", regresión equilibrada="
            f"{result['balanced_linear_mae']:.2f}"
        )

    mean_median_mae = sum(
        result["median_mae"]
        for result in cv_results
    ) / len(cv_results)

    mean_linear_mae = sum(
        result["linear_mae"]
        for result in cv_results
    ) / len(cv_results)

    mean_balanced_linear_mae = sum(
        result["balanced_linear_mae"]
        for result in cv_results
    ) / len(cv_results)

    mean_personal_median_mae = sum(
        result["personal_median_mae"]
        for result in cv_results
    ) / len(cv_results)

    print(
        "\nMAE medio por atleta en validación:"
    )
    print(
        f"Mediana: {mean_median_mae:.2f} "
        "puntos de desacoplamiento"
    )
    print(
        f"Regresión lineal: {mean_linear_mae:.2f} "
        "puntos de desacoplamiento"
    )

    print(
        f"Regresión equilibrada: "
        f"{mean_balanced_linear_mae:.2f} "
        "puntos de desacoplamiento"
    )

    print(
        f"Mediana personal: "
        f"{mean_personal_median_mae:.2f} "
        "puntos de desacoplamiento"
    )

    ridge_results = cross_validate_ridge_alphas(
        train_rows,
        (0.1, 1.0, 10.0, 100.0),
    )

    print("\nValidación Ridge:")

    for result in ridge_results:
        print(
            f"alpha={result['alpha']}: "
            f"MAE medio por atleta="
            f"{result['mean_athlete_mae']:.2f}"
        )

    best_ridge_result = min(
        ridge_results,
        key=lambda result: result["mean_athlete_mae"],
    )

    best_alpha = best_ridge_result["alpha"]

    print(
        f"Mejor alpha: {best_alpha}"
    )

    forest_results = (
        cross_validate_random_forest_configs(
            train_rows,
            (
                (3, 5),
                (5, 5),
                (5, 10),
                (None, 10),
                (None, 20),
            ),
        )
    )

    print("\nValidación Random Forest:")

    for result in forest_results:
        print(
            f"max_depth={result['max_depth']}, "
            f"min_samples_leaf="
            f"{result['min_samples_leaf']}: "
            f"MAE medio por atleta="
            f"{result['mean_athlete_mae']:.2f}"
        )

    best_forest_result = min(
        forest_results,
        key=lambda result: result["mean_athlete_mae"],
    )

    best_max_depth = best_forest_result[
        "max_depth"
    ]
    best_min_samples_leaf = best_forest_result[
        "min_samples_leaf"
    ]

    print(
        "Mejor configuración Random Forest: "
        f"max_depth={best_max_depth}, "
        f"min_samples_leaf={best_min_samples_leaf}"
    )

    baseline_mae = evaluate_median_baseline(
        train_rows,
        test_rows,
    )

    linear_model = train_response_linear_model(
        train_rows
    )

    linear_mae = evaluate_response_linear_model(
        linear_model,
        test_rows,
    )

    balanced_linear_model = (
        train_balanced_response_linear_model(
            train_rows
        )
    )

    balanced_linear_mae = (
        evaluate_response_linear_model(
            balanced_linear_model,
            test_rows,
        )
    )

    personal_median_mae = (
        evaluate_personal_median_baseline(
            test_rows
        )
    )

    ridge_model = train_response_ridge_model(
        train_rows,
        alpha=best_alpha,
    )

    ridge_mae = evaluate_response_ridge_model(
        ridge_model,
        test_rows,
    )

    forest_model = train_response_random_forest(
        train_rows,
        max_depth=best_max_depth,
        min_samples_leaf=best_min_samples_leaf,
    )

    forest_mae = evaluate_response_random_forest(
        forest_model,
        test_rows,
    )

    print("\nEvaluación final:")

    print(
        f"Filas de entrenamiento: {len(train_rows)}"
    )

    print(
        f"Filas de evaluación: {len(test_rows)}"
    )
    
    print(
        f"MAE mediana: {baseline_mae:.2f} "
        "puntos de desacoplamiento"
    )
    
    print(
        f"MAE regresión lineal: {linear_mae:.2f} "
        "puntos de desacoplamiento"
    )

    print(
        f"MAE regresión equilibrada: "
        f"{balanced_linear_mae:.2f} "
        "puntos de desacoplamiento"
    )

    print(
        f"MAE mediana personal: "
        f"{personal_median_mae:.2f} "
        "puntos de desacoplamiento"
    )

    print(
        f"MAE Ridge: {ridge_mae:.2f} "
        "puntos de desacoplamiento"
    )

    print(
        f"MAE Random Forest: {forest_mae:.2f} "
        "puntos de desacoplamiento"
    )

if __name__ == "__main__":
    main()