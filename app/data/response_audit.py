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

def collect_athlete_decoupling_comparisons(
    zip_path: str | Path,
) -> list[dict]:
    """Compara el desacoplamiento de todas las actividades válidas."""
    zip_path = Path(zip_path)

    if zip_path.suffix.lower() != ".zip":
        raise ValueError(
            "La comparación requiere un archivo ZIP."
        )

    data = read_athlete_summary(zip_path)
    athlete_id = str(data["ATHLETE"]["id"]).strip("{}")

    csv_names = list_activity_csvs(zip_path)
    csv_index = build_csv_datetime_index(csv_names)

    comparisons = []

    with zipfile.ZipFile(zip_path) as archive:
        for ride in data["RIDES"]:
            if ride.get("sport") != "Bike":
                continue

            if not has_power_and_heart_rate(ride):
                continue

            match = match_activity_csv(
                ride["date"],
                csv_index,
            )

            if match["status"] != "matched":
                continue

            try:
                samples = read_activity_samples(
                    archive,
                    match["csv_name"],
                )
            except ValueError:
                continue

            comparison = build_decoupling_comparison(
                ride,
                samples,
            )

            if comparison is None:
                continue

            comparisons.append({
                "athlete_id": athlete_id,
                "csv_name": match["csv_name"],
                **comparison,
            })

    return comparisons

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

def _segment_duration(segment: list[dict]) -> float:
    """Calcula la duración entre la primera y la última muestra."""
    if len(segment) < 2:
        return 0.0

    start = metric(segment[0].get("secs"))
    end = metric(segment[-1].get("secs"))

    return end - start

def split_segment_by_time(
    segment: list[dict],
) -> tuple[list[dict], list[dict]]:
    """Divide un tramo en dos mitades de igual duración temporal."""
    if len(segment) < 2:
        raise ValueError(
            "Se necesitan al menos dos muestras."
        )

    start = metric(segment[0].get("secs"))
    end = metric(segment[-1].get("secs"))

    if start is None or end is None or end <= start:
        raise ValueError(
            "El tramo debe tener un eje temporal creciente."
        )

    midpoint = start + (end - start) / 2

    first_half = [
        sample
        for sample in segment
        if metric(sample.get("secs")) <= midpoint
    ]

    second_half = [
        sample
        for sample in segment
        if metric(sample.get("secs")) > midpoint
    ]

    if not first_half or not second_half:
        raise ValueError(
            "No se pueden construir las dos mitades."
        )

    return first_half, second_half

def calculate_aerobic_decoupling(
    segment: list[dict],
) -> float | None:
    """Calcula el desacoplamiento potencia/FC entre ambas mitades."""
    halves = summarize_decoupling_halves(segment)

    first_power = halves["first_half_power"]
    second_power = halves["second_half_power"]

    if first_power <= 0 or second_power <= 0:
        return None

    first_ratio = halves["first_half_ratio"]
    second_ratio = halves["second_half_ratio"]

    return (
        100
        * (first_ratio - second_ratio)
        / first_ratio
    )

def extract_longest_continuous_paired_segment(
    samples: list[dict],
    *,
    max_gap_seconds: float = 5,
) -> list[dict]:
    """Extrae el tramo continuo más largo con potencia y FC válidas."""
    if max_gap_seconds <= 0:
        raise ValueError(
            "El salto máximo debe ser mayor que cero."
        )

    longest_segment = []
    current_segment = []
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

        if previous_second is None:
            current_segment = [sample]
        else:
            gap = second - previous_second

            if 0 < gap <= max_gap_seconds:
                current_segment.append(sample)
            else:
                if _segment_duration(current_segment) > _segment_duration(
                    longest_segment
                ):
                    longest_segment = current_segment

                current_segment = [sample]

        previous_second = second

    if _segment_duration(current_segment) > _segment_duration(
        longest_segment
    ):
        longest_segment = current_segment

    return longest_segment

def longest_continuous_paired_segment_seconds(
    samples: list[dict],
    *,
    max_gap_seconds: float = 5,
) -> float:
    """Calcula la duración del tramo continuo más largo con potencia y FC."""
    segment = extract_longest_continuous_paired_segment(
        samples,
        max_gap_seconds=max_gap_seconds,
    )

    return _segment_duration(segment)

def build_activity_response(
    samples: list[dict],
    *,
    min_duration_seconds: float = 20 * 60,
    max_gap_seconds: float = 5,
) -> dict | None:
    """Construye la respuesta cardiovascular de una actividad válida."""
    if min_duration_seconds <= 0:
        raise ValueError(
            "La duración mínima debe ser mayor que cero."
        )

    segment = extract_longest_continuous_paired_segment(
        samples,
        max_gap_seconds=max_gap_seconds,
    )

    duration = _segment_duration(segment)

    if duration < min_duration_seconds:
        return None

    halves = summarize_decoupling_halves(segment)
    decoupling = calculate_aerobic_decoupling(segment)
    stability = summarize_segment_stability(segment)

    if decoupling is None:
        return None

    return {
        "continuous_duration_seconds": duration,
        "paired_sample_count": len(segment),
        **halves,
        **stability,
        "aerobic_decoupling": decoupling,
    }

def build_decoupling_comparison(
    ride: dict,
    samples: list[dict],
    *,
    min_duration_seconds: float = 20 * 60,
) -> dict | None:
    """Compara el desacoplamiento calculado con el de GoldenCheetah."""
    reported_decoupling = metric(
        ride.get("METRICS", {}).get("aerobic_decoupling")
    )

    if reported_decoupling is None:
        return None

    response = build_activity_response(
        samples,
        min_duration_seconds=min_duration_seconds,
    )

    if response is None:
        return None

    calculated_decoupling = response["aerobic_decoupling"]

    return {
        "ride_date": ride["date"],
        "reported_decoupling": reported_decoupling,
        "calculated_decoupling": calculated_decoupling,
        "difference": (
            calculated_decoupling - reported_decoupling
        ),
        "continuous_duration_seconds": (
            response["continuous_duration_seconds"]
        ),
        "paired_sample_count": response["paired_sample_count"],
        "first_half_power": response["first_half_power"],
        "second_half_power": response["second_half_power"],
        "first_half_hr": response["first_half_hr"],
        "second_half_hr": response["second_half_hr"],
        "first_half_ratio": response["first_half_ratio"],
        "second_half_ratio": response["second_half_ratio"],
        "mean_power": response["mean_power"],
        "power_standard_deviation": (
            response["power_standard_deviation"]
        ),
        "power_cv": response["power_cv"],
        "zero_power_fraction": response["zero_power_fraction"],
        "power_balance_ratio": response["power_balance_ratio"],
    }

def save_decoupling_comparisons(
    comparisons: list[dict],
    output: str | Path,
) -> None:
    """Guarda las comparaciones de desacoplamiento en un CSV."""
    if not comparisons:
        raise ValueError(
            "No hay comparaciones que guardar."
        )

    output = Path(output)
    output.parent.mkdir(parents=True, exist_ok=True)

    with output.open(
        "w",
        encoding="utf-8",
        newline="",
    ) as file:
        writer = csv.DictWriter(
            file,
            fieldnames=list(comparisons[0]),
        )
        writer.writeheader()
        writer.writerows(comparisons)

def summarize_decoupling_halves(
    segment: list[dict],
) -> dict[str, float]:
    """Resume potencia, FC y su relación en cada mitad."""
    first_half, second_half = split_segment_by_time(segment)

    first_power = sum(
        metric(sample.get("power"))
        for sample in first_half
    ) / len(first_half)

    second_power = sum(
        metric(sample.get("power"))
        for sample in second_half
    ) / len(second_half)

    first_hr = sum(
        metric(sample.get("hr"))
        for sample in first_half
    ) / len(first_half)

    second_hr = sum(
        metric(sample.get("hr"))
        for sample in second_half
    ) / len(second_half)

    return {
        "first_half_power": first_power,
        "second_half_power": second_power,
        "first_half_hr": first_hr,
        "second_half_hr": second_hr,
        "first_half_ratio": (
            first_power / first_hr
        ),
        "second_half_ratio": (
            second_power / second_hr
        ),
    }

def summarize_segment_stability(
    segment: list[dict],
) -> dict[str, float | None]:
    """Resume la estabilidad de potencia del tramo seleccionado."""
    if not segment:
        raise ValueError(
            "Se necesita un tramo con muestras."
        )

    powers = [
        metric(sample.get("power"))
        for sample in segment
    ]

    mean_power = sum(powers) / len(powers)

    power_variance = sum(
        (power - mean_power) ** 2
        for power in powers
    ) / len(powers)

    power_standard_deviation = power_variance ** 0.5

    power_cv = (
        power_standard_deviation / mean_power
        if mean_power > 0
        else None
    )

    zero_power_fraction = (
        sum(power == 0 for power in powers)
        / len(powers)
    )

    halves = summarize_decoupling_halves(segment)
    maximum_half_power = max(
        halves["first_half_power"],
        halves["second_half_power"],
    )

    power_balance_ratio = (
        min(
            halves["first_half_power"],
            halves["second_half_power"],
        )
        / maximum_half_power
        if maximum_half_power > 0
        else None
    )

    return {
        "mean_power": mean_power,
        "power_standard_deviation": power_standard_deviation,
        "power_cv": power_cv,
        "zero_power_fraction": zero_power_fraction,
        "power_balance_ratio": power_balance_ratio,
    }

def is_eligible_decoupling_response(
    response: dict,
    *,
    max_power_cv: float = 0.75,
    max_zero_power_fraction: float = 0.20,
    min_power_balance_ratio: float = 0.80,
) -> bool:
    """Comprueba si una actividad es adecuada para estudiar desacoplamiento."""
    if max_power_cv < 0:
        raise ValueError(
            "El CV máximo no puede ser negativo."
        )

    if not 0 <= max_zero_power_fraction <= 1:
        raise ValueError(
            "La fracción de potencia cero debe estar entre 0 y 1."
        )

    if not 0 <= min_power_balance_ratio <= 1:
        raise ValueError(
            "El equilibrio de potencia debe estar entre 0 y 1."
        )

    return (
        response["power_cv"] <= max_power_cv
        and response["zero_power_fraction"]
        <= max_zero_power_fraction
        and response["power_balance_ratio"]
        >= min_power_balance_ratio
    )

def filter_eligible_decoupling_comparisons(
    comparisons: list[dict],
) -> list[dict]:
    """Conserva las actividades adecuadas para estudiar desacoplamiento."""
    return [
        comparison
        for comparison in comparisons
        if is_eligible_decoupling_response(comparison)
    ]

def build_response_session_features(
    ride: dict,
) -> dict[str, float] | None:
    """Extrae características de sesión utilizables antes de entrenar."""
    metrics = ride.get("METRICS", {})

    duration_seconds = metric(
        metrics.get("workout_time")
    )
    intensity_factor = metric(
        metrics.get("coggan_if")
    )
    session_tss = metric(
        metrics.get("coggan_tss")
    )

    if (
        duration_seconds is None
        or duration_seconds <= 0
        or intensity_factor is None
        or intensity_factor <= 0
        or session_tss is None
        or session_tss < 0
    ):
        return None

    return {
        "session_duration_minutes": (
            duration_seconds / 60
        ),
        "session_intensity_factor": intensity_factor,
        "session_tss": session_tss,
    }

def summarize_prior_load(
    rides: list[dict],
    target_date: str,
    *,
    days: int,
) -> dict[str, float | int]:
    """Resume la carga registrada antes de una actividad objetivo."""
    if days <= 0:
        raise ValueError(
            "El número de días debe ser mayor que cero."
        )

    target_datetime = datetime.strptime(
        target_date,
        "%Y/%m/%d %H:%M:%S UTC",
    )
    window_start = target_datetime - timedelta(
        days=days,
    )

    previous_rides = []

    for ride in rides:
        if ride.get("sport") != "Bike":
            continue

        ride_datetime = datetime.strptime(
            ride["date"],
            "%Y/%m/%d %H:%M:%S UTC",
        )

        if window_start <= ride_datetime < target_datetime:
            previous_rides.append(ride)

    tss_values = [
        metric(ride.get("METRICS", {}).get("coggan_tss"))
        for ride in previous_rides
    ]

    available_tss = [
        value
        for value in tss_values
        if value is not None
    ]

    activity_count = len(previous_rides)

    tss_coverage = (
        len(available_tss) / activity_count
        if activity_count > 0
        else 1.0
    )

    return {
        "observed_tss": sum(available_tss),
        "activity_count": activity_count,
        "tss_coverage": tss_coverage,
    }

def build_response_history_features(
    rides: list[dict],
    target_date: str,
) -> dict[str, float | int]:
    """Construye variables de carga previas a una actividad."""
    previous_7d = summarize_prior_load(
        rides,
        target_date,
        days=7,
    )
    previous_28d = summarize_prior_load(
        rides,
        target_date,
        days=28,
    )

    return {
        "previous_7d_tss": previous_7d["observed_tss"],
        "previous_7d_activity_count": (
            previous_7d["activity_count"]
        ),
        "previous_7d_tss_coverage": (
            previous_7d["tss_coverage"]
        ),
        "previous_28d_tss": previous_28d["observed_tss"],
        "previous_28d_activity_count": (
            previous_28d["activity_count"]
        ),
        "previous_28d_tss_coverage": (
            previous_28d["tss_coverage"]
        ),
    }

def has_prior_history_span(
    rides: list[dict],
    target_date: str,
    *,
    days: int = 28,
) -> bool:
    """Comprueba que existen datos desde antes del inicio de la ventana."""
    if days <= 0:
        raise ValueError(
            "El número de días debe ser mayor que cero."
        )

    target_datetime = datetime.strptime(
        target_date,
        "%Y/%m/%d %H:%M:%S UTC",
    )
    required_start = target_datetime - timedelta(
        days=days,
    )

    cycling_dates = [
        datetime.strptime(
            ride["date"],
            "%Y/%m/%d %H:%M:%S UTC",
        )
        for ride in rides
        if ride.get("sport") == "Bike"
        and datetime.strptime(
            ride["date"],
            "%Y/%m/%d %H:%M:%S UTC",
        ) < target_datetime
    ]

    return (
        bool(cycling_dates)
        and min(cycling_dates) <= required_start
    )

def build_response_dataset_row(
    athlete_id: str,
    rides: list[dict],
    ride: dict,
    comparison: dict,
) -> dict | None:
    """Construye una fila de aprendizaje para una actividad elegible."""
    if not is_eligible_decoupling_response(comparison):
        return None

    target_date = ride["date"]

    if not has_prior_history_span(
        rides,
        target_date,
        days=28,
    ):
        return None

    session_features = build_response_session_features(
        ride
    )

    if session_features is None:
        return None

    history_features = build_response_history_features(
        rides,
        target_date,
    )

    if (
        history_features["previous_7d_tss_coverage"] < 1
        or history_features["previous_28d_tss_coverage"] < 1
    ):
        return None

    return {
        "athlete_id": athlete_id,
        "activity_date": target_date,
        **session_features,
        **history_features,
        "target_aerobic_decoupling": (
            comparison["reported_decoupling"]
        ),
    }

def build_athlete_response_rows(
    data: dict,
    comparisons: list[dict],
) -> list[dict]:
    """Construye las filas de respuesta de un atleta."""
    athlete_id = str(
        data["ATHLETE"]["id"]
    ).strip("{}")

    rides = data["RIDES"]
    rides_by_date = {}

    for ride in rides:
        ride_date = ride["date"]

        if ride_date not in rides_by_date:
            rides_by_date[ride_date] = []

        rides_by_date[ride_date].append(ride)

    rows = []

    for comparison in comparisons:
        matching_rides = rides_by_date.get(
            comparison["ride_date"],
            [],
        )

        if len(matching_rides) != 1:
            continue

        row = build_response_dataset_row(
            athlete_id,
            rides,
            matching_rides[0],
            comparison,
        )

        if row is not None:
            rows.append(row)

    return rows

def save_response_dataset(
    rows: list[dict],
    output: str | Path,
) -> None:
    """Guarda el dataset de respuesta en un CSV."""
    if not rows:
        raise ValueError(
            "No hay filas de respuesta que guardar."
        )

    output = Path(output)
    output.parent.mkdir(parents=True, exist_ok=True)

    with output.open(
        "w",
        encoding="utf-8",
        newline="",
    ) as file:
        writer = csv.DictWriter(
            file,
            fieldnames=list(rows[0]),
        )
        writer.writeheader()
        writer.writerows(rows)

def main():
    parser = argparse.ArgumentParser(
        description=(
            "Audita señales de potencia y frecuencia cardiaca "
            "y construye el dataset de respuesta."
        )
    )

    parser.add_argument(
        "sources",
        nargs="+",
        type=Path,
        help="Rutas a los resúmenes JSON o ZIP de los atletas.",
    )

    parser.add_argument(
        "--signal-coverage",
        action="store_true",
        help=(
            "Analiza la cobertura de potencia y "
            "frecuencia cardiaca."
        ),
    )

    parser.add_argument(
        "--decoupling-output",
        type=Path,
        help=(
            "Guarda en CSV la comparación del desacoplamiento "
            "calculado y el informado por GoldenCheetah."
        ),
    )

    parser.add_argument(
        "--response-output",
        type=Path,
        help=(
            "Guarda el dataset de respuesta cardiovascular "
            "preparado para ML."
        ),
    )

    args = parser.parse_args()

    all_comparisons = []
    all_response_rows = []

    for path in args.sources:
        summary = audit_athlete_summary(path)

        print(
            f"Atleta {summary['athlete_id']}: "
            f"{summary['response_candidates']} candidatas de "
            f"{summary['cycling_activities']} "
            f"actividades de ciclismo"
        )

        if path.suffix.lower() != ".zip":
            continue

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

        needs_comparisons = (
            args.decoupling_output is not None
            or args.response_output is not None
        )

        if needs_comparisons:
            comparisons = (
                collect_athlete_decoupling_comparisons(
                    path
                )
            )

            print(
                "  Comparaciones de desacoplamiento válidas: "
                f"{len(comparisons)}"
            )

            if args.decoupling_output is not None:
                all_comparisons.extend(comparisons)

            if args.response_output is not None:
                response_rows = build_athlete_response_rows(
                    data,
                    comparisons,
                )

                all_response_rows.extend(response_rows)

                print(
                    "  Filas elegibles para ML: "
                    f"{len(response_rows)}"
                )

        if args.signal_coverage:
            coverage = audit_athlete_signal_coverage(
                path
            )

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

    if args.decoupling_output is not None:
        save_decoupling_comparisons(
            all_comparisons,
            args.decoupling_output,
        )

        print(
            "\nComparaciones guardadas en: "
            f"{args.decoupling_output}"
        )
        print(
            "Filas de comparación exportadas: "
            f"{len(all_comparisons)}"
        )

    if args.response_output is not None:
        save_response_dataset(
            all_response_rows,
            args.response_output,
        )

        print(
            "\nDataset de respuesta guardado en: "
            f"{args.response_output}"
        )
        print(
            "Filas de respuesta exportadas: "
            f"{len(all_response_rows)}"
        )

if __name__ == "__main__":
    main()