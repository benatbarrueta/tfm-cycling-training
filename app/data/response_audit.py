import json
import zipfile
import argparse
import csv
import io

from collections import Counter
from datetime import datetime, timedelta
from pathlib import Path
from statistics import median

from app.data.goldencheetah import metric

SUPPORTED_OFFSET_MINUTES = tuple(
    range(-14 * 60, 14 * 60 + 1, 15)
)

def has_power_and_heart_rate(ride: dict) -> bool:
    """Comprueba si el resumen tiene potencia y FC medias positivas."""
    metrics = ride.get("METRICS", {})

    average_power = metric(metrics.get("average_power"))
    average_hr = metric(metrics.get("average_hr"))

    return (
        # Ambas variables deben existir y ser mayores que cero.
        average_power is not None
        and average_power > 0
        and average_hr is not None
        and average_hr > 0
    )

def summarize_response_candidates(rides: list[dict]) -> dict[str, int]:
    """Cuenta actividades de ciclismo con potencia y FC medias válidas."""
    cycling_rides = [
        ride for ride in rides
        if ride.get("sport") == "Bike"
    ]

    candidate_count = sum(
        # Llama a has_power_and_heart_rate para cada actividad.
        has_power_and_heart_rate(ride)
        for ride in cycling_rides

    )

    return {
        "total_activities": len(rides),
        "cycling_activities": len(cycling_rides),
        "response_candidates": candidate_count,
        "cycling_without_required_metrics": (
            len(cycling_rides) - candidate_count
        ),
    }

def audit_athlete_summary(path: str | Path) -> dict:
    """Lee el resumen y cuenta las actividades candidatas."""
    data = read_athlete_summary(path)

    athlete_id = str(data["ATHLETE"]["id"]).strip("{}")
    summary = summarize_response_candidates(data["RIDES"])

    return {
        "athlete_id": athlete_id,
        **summary,
    }

def summarize_signal_coverage(samples: list[dict]) -> dict[str, int]:
    """Cuenta muestras con potencia válida y FC positiva simultáneas."""
    paired_samples = 0

    for sample in samples:
        power = metric(sample.get("power"))
        heart_rate = metric(sample.get("hr"))

        # Si power existe y heart_rate existe y es mayor que cero,
        # incrementa paired_samples.
        if power is not None and heart_rate is not None and heart_rate > 0:
            paired_samples += 1

    return {
        "total_samples": len(samples),
        "paired_samples": paired_samples,
    }

def read_activity_samples(
    archive: zipfile.ZipFile,
    csv_name: str,
) -> list[dict]:
    """Lee las muestras de un CSV desde un ZIP ya abierto."""
    with archive.open(csv_name) as raw_file:
        with io.TextIOWrapper(
            raw_file,
            encoding="utf-8-sig",
            newline="",
        ) as text_file:
            reader = csv.DictReader(text_file)

            required_columns = {"secs", "power", "hr"}

            if not required_columns.issubset(
                reader.fieldnames or []
            ):
                raise ValueError(
                    "El CSV debe contener secs, power y hr."
                )

            return list(reader)

def audit_activity_csv(
    zip_path: str | Path,
    csv_name: str,
) -> dict[str, int]:
    """Audita las muestras de un CSV contenido en un ZIP."""
    with zipfile.ZipFile(zip_path) as archive:
        samples = read_activity_samples(
            archive,
            csv_name,
        )

    return summarize_signal_coverage(samples)

def list_activity_csvs(zip_path: str | Path) -> list[str]:
    """Devuelve los nombres de los CSV del ZIP, ordenados."""
    with zipfile.ZipFile(zip_path) as archive:
        csv_names = [
            name
            for name in archive.namelist()

            if name.lower().endswith(".csv") and not name.startswith("__MACOSX/")
        ]

    return sorted(csv_names)

def read_athlete_summary(path: str | Path) -> dict:
    """Lee el contenido del resumen desde un JSON o un ZIP."""
    path = Path(path)

    if path.suffix.lower() == ".zip":
        with zipfile.ZipFile(path) as archive:
            json_files = [
                name
                for name in archive.namelist()
                if name.lower().endswith(".json")
                and not name.startswith("__MACOSX/")
            ]

            if len(json_files) != 1:
                raise ValueError(
                    "El ZIP debe contener exactamente un resumen JSON."
                )

            with archive.open(json_files[0]) as file:
                data = json.loads(
                    file.read().decode("utf-8-sig")
                )
    else:
        with path.open(encoding="utf-8-sig") as file:
            data = json.load(file)

    return data

def parse_csv_datetime(csv_name: str) -> datetime:
    """Extrae la fecha del nombre del CSV, sin asumir zona horaria."""
    filename = Path(csv_name).stem

    return datetime.strptime(
        filename,
        "%Y_%m_%d_%H_%M_%S"
    )

def find_csv_candidates(
    ride_date_utc: str,
    csv_names: list[str],
    *,
    offset_minutes: int,
) -> list[str]:
    """Busca CSV cuya fecha coincide con UTC más el desfase indicado."""
    ride_datetime = datetime.strptime(
        ride_date_utc,
        "%Y/%m/%d %H:%M:%S UTC",
    )

    expected_datetime = ride_datetime + timedelta(
        minutes=offset_minutes,
    )

    candidates = []

    for csv_name in csv_names:
        try:
            csv_datetime = parse_csv_datetime(csv_name)
        except ValueError:
            continue

        if csv_datetime == expected_datetime:
            candidates.append(csv_name)

    return sorted(candidates)

def count_matches_for_offset(
    rides: list[dict],
    csv_names: list[str],
    *,
    offset_minutes: int,
) -> dict[str, int]:
    """Cuenta coincidencias únicas, ausentes y ambiguas para un desfase."""
    unique_matches = 0
    missing_matches = 0
    ambiguous_matches = 0

    for ride in rides:
        if ride.get("sport") != "Bike":
            continue

        candidates = find_csv_candidates(
            ride["date"],
            csv_names,
            offset_minutes=offset_minutes,
        )

        if len(candidates) == 1:
            unique_matches += 1
        elif len(candidates) == 0:
            missing_matches += 1
        else:
            ambiguous_matches += 1

    return {
        "offset_minutes": offset_minutes,
        "unique_matches": unique_matches,
        "missing_matches": missing_matches,
        "ambiguous_matches": ambiguous_matches,
    }

def find_best_hour_offset(
    rides: list[dict],
    csv_names: list[str],
) -> dict[str, int]:
    """Encuentra el desfase horario con más coincidencias únicas."""
    results = [
        count_matches_for_offset(
            rides,
            csv_names,
            offset_minutes=offset_minutes,
        )
        for offset_minutes in SUPPORTED_OFFSET_MINUTES
    ]

    best_count = max(
        result["unique_matches"]
        for result in results
    )

    best_results = [
        result
        for result in results
        if result["unique_matches"] == best_count
    ]

    if best_count == 0:
        raise ValueError(
            "Ningún desfase horario produce coincidencias."
        )

    if len(best_results) != 1:
        raise ValueError(
            "Varios desfases producen el mismo número de coincidencias."
        )

    return best_results[0]

def summarize_activity_offsets(
    rides: list[dict],
    csv_names: list[str],
) -> dict:
    """Resume los desfases con coincidencia única por actividad de ciclismo."""
    offsets = []
    unmatched = 0
    ambiguous = 0

    csv_index = build_csv_datetime_index(csv_names)

    for ride in rides:
        if ride.get("sport") != "Bike":
            continue

        ride_datetime = datetime.strptime(
            ride["date"],
            "%Y/%m/%d %H:%M:%S UTC",
        )

        matching_offsets = []
        activity_is_ambiguous = False

        for offset_minutes in SUPPORTED_OFFSET_MINUTES:
            expected_datetime = ride_datetime + timedelta(
                minutes=offset_minutes,
            )

            candidates = csv_index.get(
                expected_datetime,
                [],
            )

            if len(candidates) == 1:
                matching_offsets.append(offset_minutes)
            elif len(candidates) > 1:
                activity_is_ambiguous = True
                break

        if activity_is_ambiguous:
            ambiguous += 1
        elif len(matching_offsets) == 1:
            offsets.append(matching_offsets[0])
        elif len(matching_offsets) == 0:
            unmatched += 1
        else:
            ambiguous += 1

    return {
        "offset_counts": dict(
            sorted(Counter(offsets).items())
        ),
        "matched_activities": len(offsets),
        "unmatched_activities": unmatched,
        "ambiguous_activities": ambiguous,
    }

def build_csv_datetime_index(
    csv_names: list[str],
) -> dict[datetime, list[str]]:
    """Agrupa los CSV por la fecha incluida en su nombre."""
    index = {}

    for csv_name in csv_names:
        try:
            csv_datetime = parse_csv_datetime(csv_name)
        except ValueError:
            continue

        if csv_datetime not in index:
            index[csv_datetime] = []

        index[csv_datetime].append(csv_name)

    for names in index.values():
        names.sort()

    return index

def find_nearest_csv(
    ride_date_utc: str,
    csv_names: list[str],
) -> tuple[str, float] | None:
    """Devuelve el CSV más cercano y su diferencia en minutos."""
    ride_datetime = datetime.strptime(
        ride_date_utc,
        "%Y/%m/%d %H:%M:%S UTC",
    )

    dated_csvs = []

    for csv_name in csv_names:
        try:
            csv_datetime = parse_csv_datetime(csv_name)
        except ValueError:
            continue

        difference_minutes = (
            csv_datetime - ride_datetime
        ).total_seconds() / 60

        dated_csvs.append((
            csv_name,
            difference_minutes,
        ))

    if not dated_csvs:
        return None

    return min(
        dated_csvs,
        key=lambda item: abs(item[1]),
    )

def collect_unmatched_examples(
    rides: list[dict],
    csv_names: list[str],
    *,
    limit: int = 5,
) -> list[dict]:
    """Recoge ejemplos sin coincidencia exacta y su CSV más cercano."""
    if limit <= 0:
        raise ValueError("El límite debe ser mayor que cero.")

    csv_index = build_csv_datetime_index(csv_names)
    examples = []

    for ride in rides:
        if ride.get("sport") != "Bike":
            continue

        ride_datetime = datetime.strptime(
            ride["date"],
            "%Y/%m/%d %H:%M:%S UTC",
        )

        has_match = False

        for offset_minutes in SUPPORTED_OFFSET_MINUTES:
            expected_datetime = ride_datetime + timedelta(
                minutes=offset_minutes,
            )

            if csv_index.get(expected_datetime):
                has_match = True
                break

        if has_match:
            continue

        nearest = find_nearest_csv(
            ride["date"],
            csv_names,
        )

        examples.append({
            "ride_date_utc": ride["date"],
            "nearest_csv": (
                nearest[0] if nearest is not None else None
            ),
            "difference_minutes": (
                nearest[1] if nearest is not None else None
            ),
        })

        if len(examples) == limit:
            break

    return examples

def match_activity_csv(
    ride_date_utc: str,
    csv_index: dict[datetime, list[str]],
) -> dict:
    """Relaciona una actividad con un único CSV."""
    ride_datetime = datetime.strptime(
        ride_date_utc,
        "%Y/%m/%d %H:%M:%S UTC",
    )

    matches = []

    for offset_minutes in SUPPORTED_OFFSET_MINUTES:
        expected_datetime = ride_datetime + timedelta(
            minutes=offset_minutes,
        )

        for csv_name in csv_index.get(expected_datetime, []):
            matches.append({
                "csv_name": csv_name,
                "offset_minutes": offset_minutes,
            })

    if len(matches) == 0:
        return {
            "status": "missing",
            "csv_name": None,
            "offset_minutes": None,
        }

    if len(matches) > 1:
        return {
            "status": "ambiguous",
            "csv_name": None,
            "offset_minutes": None,
        }

    return {
        "status": "matched",
        **matches[0],
    }

def calculate_signal_coverage(
    samples: list[dict],
) -> float | None:
    """Calcula la proporción de muestras con potencia y FC válidas."""
    summary = summarize_signal_coverage(samples)

    if summary["total_samples"] == 0:
        return None

    return (
        summary["paired_samples"]
        / summary["total_samples"]
    )

def audit_athlete_signal_coverage(
    zip_path: str | Path,
) -> dict:
    """Audita la cobertura de potencia y FC de un atleta."""
    zip_path = Path(zip_path)

    if zip_path.suffix.lower() != ".zip":
        raise ValueError(
            "La auditoría de señales requiere un archivo ZIP."
        )

    data = read_athlete_summary(zip_path)
    athlete_id = str(data["ATHLETE"]["id"]).strip("{}")

    csv_names = list_activity_csvs(zip_path)
    csv_index = build_csv_datetime_index(csv_names)

    candidate_count = 0
    matched_count = 0
    missing_count = 0
    ambiguous_count = 0
    invalid_csv_count = 0
    empty_csv_count = 0

    total_samples = 0
    paired_samples = 0
    coverage_values = []

    duration_at_least_20_minutes = 0
    duration_at_least_30_minutes = 0
    duration_at_least_60_minutes = 0
    activities_with_non_increasing_time = 0
    activities_with_gap_over_5_seconds = 0
    activities_with_gap_over_60_seconds = 0
    activities_without_valid_time = 0

    continuous_segment_at_least_10_minutes = 0
    continuous_segment_at_least_20_minutes = 0
    continuous_segment_at_least_30_minutes = 0

    with zipfile.ZipFile(zip_path) as archive:
        for ride in data["RIDES"]:
            if ride.get("sport") != "Bike":
                continue

            if not has_power_and_heart_rate(ride):
                continue

            candidate_count += 1

            match = match_activity_csv(
                ride["date"],
                csv_index,
            )

            if match["status"] == "missing":
                missing_count += 1
                continue

            if match["status"] == "ambiguous":
                ambiguous_count += 1
                continue

            try:
                samples = read_activity_samples(
                    archive,
                    match["csv_name"],
                )
            except ValueError:
                invalid_csv_count += 1
                continue

            summary = summarize_signal_coverage(samples)

            if summary["total_samples"] == 0:
                empty_csv_count += 1
                continue

            matched_count += 1
            total_samples += summary["total_samples"]
            paired_samples += summary["paired_samples"]

            coverage_values.append(
                summary["paired_samples"]
                / summary["total_samples"]
            )

            quality = summarize_activity_signal_quality(
                samples
            )

            longest_segment = (
                longest_continuous_paired_segment_seconds(
                    samples,
                    max_gap_seconds=5,
                )
            )

            if longest_segment >= 10 * 60:
                continuous_segment_at_least_10_minutes += 1

            if longest_segment >= 20 * 60:
                continuous_segment_at_least_20_minutes += 1

            if longest_segment >= 30 * 60:
                continuous_segment_at_least_30_minutes += 1

            elapsed_seconds = quality["elapsed_seconds"]
            max_gap_seconds = quality["max_gap_seconds"]

            if elapsed_seconds is None:
                activities_without_valid_time += 1
            else:
                if elapsed_seconds >= 20 * 60:
                    duration_at_least_20_minutes += 1

                if elapsed_seconds >= 30 * 60:
                    duration_at_least_30_minutes += 1

                if elapsed_seconds >= 60 * 60:
                    duration_at_least_60_minutes += 1

            if quality["non_increasing_steps"] > 0:
                activities_with_non_increasing_time += 1

            if quality["gaps_over_5_seconds"] > 0:
                activities_with_gap_over_5_seconds += 1

            if (
                max_gap_seconds is not None
                and max_gap_seconds > 60
            ):
                activities_with_gap_over_60_seconds += 1

    pooled_coverage = (
        paired_samples / total_samples
        if total_samples > 0
        else None
    )

    median_coverage = (
        median(coverage_values)
        if coverage_values
        else None
    )

    return {
        "athlete_id": athlete_id,
        "response_candidates": candidate_count,
        "matched_candidates": matched_count,
        "missing_candidates": missing_count,
        "ambiguous_candidates": ambiguous_count,
        "invalid_csv_candidates": invalid_csv_count,
        "empty_csv_candidates": empty_csv_count,
        "coverage_at_least_50": sum(
            value >= 0.50
            for value in coverage_values
        ),
        "coverage_at_least_80": sum(
            value >= 0.80
            for value in coverage_values
        ),
        "coverage_at_least_90": sum(
            value >= 0.90
            for value in coverage_values
        ),
        "pooled_coverage": pooled_coverage,
        "median_activity_coverage": median_coverage,
                "duration_at_least_20_minutes": (
            duration_at_least_20_minutes
        ),
        "duration_at_least_30_minutes": (
            duration_at_least_30_minutes
        ),
        "duration_at_least_60_minutes": (
            duration_at_least_60_minutes
        ),
        "activities_with_non_increasing_time": (
            activities_with_non_increasing_time
        ),
        "activities_with_gap_over_5_seconds": (
            activities_with_gap_over_5_seconds
        ),
        "activities_with_gap_over_60_seconds": (
            activities_with_gap_over_60_seconds
        ),
        "activities_without_valid_time": (
            activities_without_valid_time
        ),
        "continuous_segment_at_least_10_minutes": (
            continuous_segment_at_least_10_minutes
        ),
        "continuous_segment_at_least_20_minutes": (
            continuous_segment_at_least_20_minutes
        ),
        "continuous_segment_at_least_30_minutes": (
            continuous_segment_at_least_30_minutes
        ),
    }

def summarize_time_axis(samples: list[dict]) -> dict:
    """Analiza continuidad y duración del eje temporal."""
    seconds = []
    invalid_time_samples = 0

    for sample in samples:
        value = metric(sample.get("secs"))

        if value is None:
            invalid_time_samples += 1
        else:
            seconds.append(value)

    if not seconds:
        return {
            "valid_time_samples": 0,
            "invalid_time_samples": invalid_time_samples,
            "elapsed_seconds": None,
            "non_increasing_steps": 0,
            "gaps_over_5_seconds": 0,
            "max_gap_seconds": None,
        }

    gaps = [
        current - previous
        for previous, current in zip(
            seconds,
            seconds[1:],
        )
    ]

    positive_gaps = [
        gap for gap in gaps
        if gap > 0
    ]

    return {
        "valid_time_samples": len(seconds),
        "invalid_time_samples": invalid_time_samples,
        "elapsed_seconds": seconds[-1] - seconds[0],
        "non_increasing_steps": sum(
            gap <= 0 for gap in gaps
        ),
        "gaps_over_5_seconds": sum(
            gap > 5 for gap in positive_gaps
        ),
        "max_gap_seconds": (
            max(positive_gaps)
            if positive_gaps
            else None
        ),
    }

def summarize_activity_signal_quality(
    samples: list[dict],
) -> dict:
    """Resume cobertura y continuidad temporal de una actividad."""
    return {
        "signal_coverage": calculate_signal_coverage(samples),
        **summarize_time_axis(samples),
    }

def longest_continuous_paired_segment_seconds(
    samples: list[dict],
    *,
    max_gap_seconds: float = 5,
) -> float:
    """Calcula el tramo continuo más largo con potencia y FC."""
    if max_gap_seconds <= 0:
        raise ValueError(
            "El salto máximo debe ser mayor que cero."
        )

    longest_duration = 0.0
    segment_start = None
    previous_second = None

    for sample in samples:
        second = metric(sample.get("secs"))
        power = metric(sample.get("power"))
        heart_rate = metric(sample.get("hr"))

        has_paired_signal = (
            second is not None
            and power is not None
            and heart_rate is not None
            and heart_rate > 0
        )

        if not has_paired_signal:
            continue

        if segment_start is None:
            segment_start = second
            previous_second = second
            continue

        gap = second - previous_second

        if 0 < gap <= max_gap_seconds:
            previous_second = second
            longest_duration = max(
                longest_duration,
                previous_second - segment_start,
            )
        else:
            segment_start = second
            previous_second = second

    return longest_duration

def main():
    parser = argparse.ArgumentParser(
        description="Cuenta actividades con potencia y frecuencia cardiaca."
    )

    parser.add_argument(
        "sources",
        nargs="+",
        type=Path,
        help="Rutas a los resúmenes JSON de los atletas.",
    )

    parser.add_argument(
        "--signal-coverage",
        action="store_true",
        help="Analiza la cobertura de potencia y frecuencia cardiaca.",
    )

    args = parser.parse_args()

    for path in args.sources:
        summary = audit_athlete_summary(path)

        print(
            f"Atleta {summary['athlete_id']}: "
            f"{summary['response_candidates']} candidatas de "
            f"{summary['cycling_activities']} actividades de ciclismo"
        )

        if path.suffix.lower() == ".zip":
            data = read_athlete_summary(path)
            csv_names = list_activity_csvs(path)

            offset_summary = summarize_activity_offsets(
                data["RIDES"],
                csv_names,
            )

            print(
                f"  CSV encontrados: {len(csv_names)} | "
                f"emparejadas: "
                f"{offset_summary['matched_activities']} | "
                f"sin pareja: "
                f"{offset_summary['unmatched_activities']} | "
                f"ambiguas: "
                f"{offset_summary['ambiguous_activities']}"
            )

            print(
                f"  Desfases: "
                f"{offset_summary['offset_counts']}"
            )

            if offset_summary["unmatched_activities"] > 0:
                examples = collect_unmatched_examples(
                    data["RIDES"],
                    csv_names,
                    limit=5,
                )

                print("  Ejemplos sin coincidencia exacta:")

                for example in examples:
                    difference = example["difference_minutes"]

                    difference_text = (
                        f"{difference:.2f} minutos"
                        if difference is not None
                        else "sin CSV disponible"
                    )

                    print(
                        f"    JSON: "
                        f"{example['ride_date_utc']} | "
                        f"CSV cercano: "
                        f"{example['nearest_csv']} | "
                        f"diferencia: {difference_text}"
                    )

            if args.signal_coverage:
                coverage = audit_athlete_signal_coverage(path)

                print("  Cobertura de señales:")

                print(
                    f"    candidatas: "
                    f"{coverage['response_candidates']} | "
                    f"emparejadas: "
                    f"{coverage['matched_candidates']} | "
                    f"sin pareja: "
                    f"{coverage['missing_candidates']} | "
                    f"ambiguas: "
                    f"{coverage['ambiguous_candidates']} | "
                    f"CSV inválidos: "
                    f"{coverage['invalid_csv_candidates']} | "
                    f"CSV vacíos: "
                    f"{coverage['empty_csv_candidates']}"
                )

                print(
                    f"    cobertura >= 50 %: "
                    f"{coverage['coverage_at_least_50']} | "
                    f">= 80 %: "
                    f"{coverage['coverage_at_least_80']} | "
                    f">= 90 %: "
                    f"{coverage['coverage_at_least_90']}"
                )

                pooled = coverage["pooled_coverage"]
                activity_median = coverage[
                    "median_activity_coverage"
                ]

                pooled_text = (
                    f"{pooled:.2%}"
                    if pooled is not None
                    else "sin datos"
                )

                median_text = (
                    f"{activity_median:.2%}"
                    if activity_median is not None
                    else "sin datos"
                )

                print(
                    f"    cobertura global: {pooled_text} | "
                    f"mediana por actividad: {median_text}"
                )

                print(
                    f"    duración >= 20 min: "
                    f"{coverage['duration_at_least_20_minutes']} | "
                    f">= 30 min: "
                    f"{coverage['duration_at_least_30_minutes']} | "
                    f">= 60 min: "
                    f"{coverage['duration_at_least_60_minutes']}"
                )

                print(
                    f"    tiempo no creciente: "
                    f"{coverage['activities_with_non_increasing_time']} | "
                    f"con saltos > 5 s: "
                    f"{coverage['activities_with_gap_over_5_seconds']} | "
                    f"con saltos > 60 s: "
                    f"{coverage['activities_with_gap_over_60_seconds']} | "
                    f"sin tiempo válido: "
                    f"{coverage['activities_without_valid_time']}"
                )

                print(
                    f"    tramo continuo >= 10 min: "
                    f"{coverage['continuous_segment_at_least_10_minutes']} | "
                    f">= 20 min: "
                    f"{coverage['continuous_segment_at_least_20_minutes']} | "
                    f">= 30 min: "
                    f"{coverage['continuous_segment_at_least_30_minutes']}"
                )


if __name__ == "__main__":
    main()