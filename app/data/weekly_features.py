import csv
from pathlib import Path
from datetime import date, timedelta

def calculate_tss_change(
    previous_tss: float,
    current_tss: float,
) -> float | None:
    """Calcula el cambio porcentual de carga entre dos semanas."""
    if previous_tss < 0 or current_tss < 0:
        raise ValueError("Los valores de TSS no pueden ser negativos.")

    if previous_tss == 0:
        return None  # Evita la división por cero si la TSS anterior es cero
    return (current_tss - previous_tss) / previous_tss * 100

def build_tss_features(
    weekly_tss: list[float],
) -> dict[str, float | None]:
    """Construye variables a partir de cuatro semanas, de antigua a reciente."""
    if len(weekly_tss) != 4:
        raise ValueError("Se requieren exactamente cuatro semanas de TSS.")

    if any(tss < 0 for tss in weekly_tss):
        raise ValueError("Los valores de TSS no pueden ser negativos.")

    return {
        "tss_latest": weekly_tss[-1],
        "tss_previous": weekly_tss[-2],
        "tss_mean_4w": sum(weekly_tss) / 4,
        "tss_change_pct": calculate_tss_change(
            weekly_tss[-2],
            weekly_tss[-1],
        ),
    }

def load_weekly_rows(path: str | Path) -> list[dict]:
    """Lee el CSV semanal y convierte los campos necesarios."""
    rows = []

    with Path(path).open(encoding="utf-8", newline="") as file:
        for row in csv.DictReader(file):
            # Convierte weekly_tss a float, o a None si está vacío.
            # Convierte usable_load_week de texto a booleano.
            row["weekly_tss"] = float(row["weekly_tss"]) if row["weekly_tss"] else None
            row["usable_load_week"] = row["usable_load_week"] == "True"
            rows.append(row)

    return rows

def group_rows_by_athlete(rows: list[dict]) -> dict[str, list[dict]]:
    """Agrupa las filas por atleta y las ordena por semana."""
    grouped = {}

    for row in rows:
        athlete_id = row["athlete_id"]

        if athlete_id not in grouped:
            grouped[athlete_id] = []

        # Añade la fila a la lista de este atleta.
        grouped[athlete_id].append(row)

    for athlete_rows in grouped.values():
        # Ordena esta lista por week_start.
        athlete_rows.sort(key=lambda x: x["week_start"])

    return grouped

def has_four_consecutive_weeks(rows: list[dict]) -> bool:
    """Comprueba cuatro semanas ordenadas, separadas por siete días."""
    if len(rows) != 4:
        return False

    dates = [
        date.fromisoformat(row["week_start"])
        for row in rows
    ]

    for previous, current in zip(dates, dates[1:]):
        # Si la diferencia no es de siete días, devuelve False.
        if (current - previous) != timedelta(days=7):
            return False

    return True

def build_feature_rows(rows: list[dict]) -> list[dict]:
    """Genera variables para ventanas de cuatro semanas válidas."""
    feature_rows = []
    grouped = group_rows_by_athlete(rows)

    for athlete_id, athlete_rows in grouped.items():
        for start in range(len(athlete_rows) - 3):
            window = athlete_rows[start:start + 4]

            if not has_four_consecutive_weeks(window):
                continue

            if not all(row["usable_load_week"] for row in window):
                continue

            if any(row["weekly_tss"] is None for row in window):
                continue

            features = build_tss_features([row["weekly_tss"] for row in window])
            feature_rows.append({
                "athlete_id": athlete_id,
                "window_start": window[0]["week_start"],
                "window_end": window[-1]["week_start"],
                **features,
            })

    return feature_rows

def build_labeled_rows(rows: list[dict]) -> list[dict]:
    """Añade el TSS observado de la semana siguiente a cada ventana."""
    feature_rows = build_feature_rows(rows)

    weekly_lookup = {
        (row["athlete_id"], row["week_start"]): row
        for row in rows
    }

    labeled_rows = []

    for features in feature_rows:
        next_week = (
            date.fromisoformat(features["window_end"])
            + timedelta(days=7)
        ).isoformat()

        target = weekly_lookup.get(
            (features["athlete_id"], next_week)
        )

        if target is None:
            continue

        if not target["usable_load_week"]:
            continue

        if target["weekly_tss"] is None:
            continue

        labeled_rows.append({
            **features,
            "target_week": next_week,
            "next_week_tss": target["weekly_tss"],
        })

    return labeled_rows

def main():
    import argparse

    parser = argparse.ArgumentParser(
        description="Genera variables de TSS a partir del CSV semanal."
    )
    parser.add_argument("input", type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument(
        "--with-target",
        action="store_true",
        help="Incluye el TSS observado de la semana siguiente.",
    )
    args = parser.parse_args()

    rows = load_weekly_rows(args.input)
    
    if args.with_target:
        features = build_labeled_rows(rows)
    else:
        features = build_feature_rows(rows)

    if not features:
        print("No se encontraron ventanas válidas.")
        return

    args.output.parent.mkdir(parents=True, exist_ok=True)

    with args.output.open("w", encoding="utf-8", newline="") as file:
        writer = csv.DictWriter(file, fieldnames=list(features[0]))
        writer.writeheader()
        writer.writerows(features)

    print(f"Ventanas exportadas: {len(features)}")
    print(f"Atletas: {len({row['athlete_id'] for row in features})}")
    print(f"Archivo: {args.output}")

if __name__ == "__main__":
    main()