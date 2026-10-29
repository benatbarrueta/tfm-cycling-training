from __future__ import annotations

from datetime import datetime, timezone
from hashlib import sha256
from io import BytesIO
from pathlib import Path
import re
from collections import deque
from statistics import mean
from xml.etree import ElementTree

from app.data.response_audit import (
    build_activity_response,
    longest_continuous_paired_segment_seconds,
)
from app.services.metrics import calculate_if, calculate_tss


MAX_ACTIVITY_FILE_BYTES = 20 * 1024 * 1024


def _local_name(tag: str) -> str:
    return tag.rsplit("}", 1)[-1]


def _first_text(element: ElementTree.Element, name: str) -> str | None:
    for child in element.iter():
        if _local_name(child.tag) == name and child.text:
            return child.text.strip()
    return None


def _number(value: object) -> float | None:
    try:
        result = float(value)  # type: ignore[arg-type]
    except (TypeError, ValueError):
        return None
    return result if result >= 0 else None


def _activity_title(filename: str) -> str:
    stem = Path(filename).stem.strip()
    if not stem or re.fullmatch(r"activity[_ -]?\d+", stem, flags=re.IGNORECASE):
        return "Actividad de ciclismo"
    return stem.replace("_", " ").replace("-", " ").strip()


def _parse_timestamp(value: str) -> datetime:
    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed


def _decoupling(samples: list[dict]) -> tuple[float | None, str | None]:
    continuous_seconds = longest_continuous_paired_segment_seconds(samples)
    try:
        response = build_activity_response(samples)
    except ValueError:
        response = None
    if response is not None:
        return round(float(response["aerobic_decoupling"]), 2), None
    if not samples:
        return None, (
            "Desacoplamiento no disponible: el archivo no contiene potencia "
            "y frecuencia cardiaca simultáneas."
        )
    return None, (
        "Desacoplamiento no disponible: el tramo continuo más largo con "
        f"potencia y frecuencia cardiaca dura {continuous_seconds / 60:.1f} min "
        "y se necesitan al menos 20 min."
    )


def _normalized_power(
    samples: list[tuple[datetime, float | None]],
    *,
    window_seconds: int = 30,
    max_gap_seconds: int = 5,
) -> float | None:
    """Calculate Coggan normalized power from a timestamped power stream."""
    if window_seconds <= 0:
        raise ValueError("La ventana debe ser positiva.")

    rolling: deque[float] = deque(maxlen=window_seconds)
    fourth_powers: list[float] = []
    previous_timestamp: datetime | None = None
    previous_power: float | None = None

    for timestamp, power in samples:
        if previous_timestamp is None:
            previous_timestamp = timestamp
            previous_power = power
            continue

        gap = int((timestamp - previous_timestamp).total_seconds())
        if gap <= 0 or gap > max_gap_seconds:
            rolling.clear()
        elif previous_power is not None:
            for _ in range(gap):
                rolling.append(previous_power)
                if len(rolling) == window_seconds:
                    rolling_average = sum(rolling) / window_seconds
                    fourth_powers.append(rolling_average**4)

        previous_timestamp = timestamp
        previous_power = power

    if not fourth_powers:
        return None
    return (mean(fourth_powers)) ** 0.25


def _complete_power_metrics(
    activity: dict,
    ftp: float | None,
    warnings: dict[str, str],
) -> dict:
    normalized_power = _number(activity.get("normalized_power"))
    if normalized_power is None or normalized_power <= 0:
        warnings.setdefault(
            "normalized_power",
            "No se ha podido calcular: se necesitan al menos 30 segundos "
            "continuos con datos de potencia.",
        )
        warnings.setdefault(
            "intensity_factor",
            "No se ha podido calcular porque falta la potencia normalizada.",
        )
        warnings.setdefault(
            "tss",
            "No se ha podido calcular porque falta la potencia normalizada.",
        )
        return activity

    if ftp is None or ftp <= 0:
        warning = "No se ha podido calcular: configura un FTP válido en tu perfil."
        warnings.setdefault("intensity_factor", warning)
        warnings.setdefault("tss", warning)
        return activity

    if activity.get("intensity_factor") is None:
        activity["intensity_factor"] = round(calculate_if(normalized_power, ftp), 3)
    if activity.get("tss") is None:
        activity["tss"] = round(
            calculate_tss(
                duration_seconds=float(activity["duration_minutes"]) * 60,
                normalized_power=normalized_power,
                ftp=ftp,
            ),
            2,
        )
    return activity


def _missing_source_warnings(activity: dict) -> dict[str, str]:
    warnings: dict[str, str] = activity.pop("_import_warnings", {})
    if activity.get("distance_km") is None:
        warnings.setdefault(
            "distance_km",
            "El archivo no contiene una distancia válida.",
        )
    if activity.get("average_power") is None:
        warnings.setdefault(
            "average_power",
            "El archivo no contiene datos de potencia.",
        )
    if activity.get("average_heart_rate") is None:
        warnings.setdefault(
            "average_heart_rate",
            "El archivo no contiene datos de frecuencia cardiaca.",
        )
    return warnings


def parse_tcx(content: bytes, filename: str) -> dict:
    try:
        root = ElementTree.fromstring(content)
    except ElementTree.ParseError as exc:
        raise ValueError("El archivo TCX no contiene XML válido.") from exc

    activity = next((item for item in root.iter() if _local_name(item.tag) == "Activity"), None)
    if activity is None:
        raise ValueError("El archivo TCX no contiene ninguna actividad.")

    identifier = _first_text(activity, "Id")
    points = [item for item in activity.iter() if _local_name(item.tag) == "Trackpoint"]
    point_rows: list[tuple[datetime, float | None, float | None]] = []
    distances: list[float] = []
    for point in points:
        time_text = _first_text(point, "Time")
        if time_text is None:
            continue
        timestamp = _parse_timestamp(time_text)
        watts = _number(_first_text(point, "Watts"))
        heart_rate = _number(_first_text(point, "Value"))
        distance = _number(_first_text(point, "DistanceMeters"))
        if distance is not None:
            distances.append(distance)
        point_rows.append((timestamp, watts, heart_rate))

    if identifier is None and not point_rows:
        raise ValueError("El archivo TCX no contiene una fecha válida.")
    started_at = _parse_timestamp(identifier) if identifier else point_rows[0][0]

    lap_durations = [
        _number(_first_text(lap, "TotalTimeSeconds"))
        for lap in activity.iter()
        if _local_name(lap.tag) == "Lap"
    ]
    duration_seconds = sum(value for value in lap_durations if value is not None)
    if duration_seconds <= 0 and len(point_rows) >= 2:
        duration_seconds = (point_rows[-1][0] - point_rows[0][0]).total_seconds()
    if duration_seconds <= 0:
        raise ValueError("No se ha podido obtener la duración de la actividad.")

    power_values = [row[1] for row in point_rows if row[1] is not None]
    heart_values = [row[2] for row in point_rows if row[2] is not None and row[2] > 0]
    signal = [
        {"secs": (timestamp - started_at).total_seconds(), "power": watts, "hr": heart_rate}
        for timestamp, watts, heart_rate in point_rows
        if watts is not None and heart_rate is not None and heart_rate > 0
    ]

    def named_metric(*names: str) -> float | None:
        for name in names:
            value = _number(_first_text(activity, name))
            if value is not None:
                return value
        return None

    aerobic_decoupling, decoupling_warning = _decoupling(signal)
    title = _activity_title(filename)
    normalized_power = named_metric("NormalizedPower", "NormalizedBikePower")
    if normalized_power is None:
        normalized_power = _normalized_power(
            [(timestamp, watts) for timestamp, watts, _ in point_rows]
        )

    return {
        "title": title,
        "started_at": started_at,
        "sport": "CYCLING",
        "duration_minutes": round(duration_seconds / 60, 2),
        "distance_km": round(max(distances) / 1000, 3) if distances else None,
        "average_power": named_metric("AvgWatts") or (round(mean(power_values), 2) if power_values else None),
        "normalized_power": round(normalized_power, 2) if normalized_power is not None else None,
        "average_heart_rate": round(mean(heart_values), 2) if heart_values else None,
        "intensity_factor": named_metric("IntensityFactor"),
        "tss": named_metric("TrainingStressScore", "TSS"),
        "aerobic_decoupling": aerobic_decoupling,
        "notes": None,
        "_import_warnings": (
            {"aerobic_decoupling": decoupling_warning}
            if decoupling_warning
            else {}
        ),
    }


def parse_fit(content: bytes, filename: str) -> dict:
    try:
        from fitparse import FitFile
    except ImportError as exc:
        raise ValueError("El servidor no tiene habilitada la importación FIT.") from exc

    try:
        fit = FitFile(BytesIO(content))
        session = next(iter(fit.get_messages("session")), None)
        records = list(fit.get_messages("record"))
    except Exception as exc:
        raise ValueError("El archivo FIT no es válido o está dañado.") from exc
    if session is None:
        raise ValueError("El archivo FIT no contiene una sesión.")

    values = session.get_values()
    started_at = values.get("start_time") or values.get("timestamp")
    if not isinstance(started_at, datetime):
        raise ValueError("El archivo FIT no contiene una fecha válida.")
    if started_at.tzinfo is None:
        started_at = started_at.replace(tzinfo=timezone.utc)

    samples: list[dict] = []
    power_rows: list[tuple[datetime, float | None]] = []
    for record in records:
        row = record.get_values()
        timestamp = row.get("timestamp")
        if not isinstance(timestamp, datetime):
            continue
        if timestamp.tzinfo is None:
            timestamp = timestamp.replace(tzinfo=timezone.utc)
        power = _number(row.get("power"))
        samples.append({
            "secs": (timestamp - started_at).total_seconds(),
            "power": power,
            "hr": _number(row.get("heart_rate")),
        })
        power_rows.append((timestamp, power))

    duration = _number(values.get("total_timer_time") or values.get("total_elapsed_time"))
    if duration is None or duration <= 0:
        raise ValueError("No se ha podido obtener la duración de la actividad.")
    aerobic_decoupling, decoupling_warning = _decoupling(samples)
    normalized_power = _number(values.get("normalized_power"))
    if normalized_power is None:
        normalized_power = _normalized_power(power_rows)
    power_values = [sample["power"] for sample in samples if sample["power"] is not None]
    heart_values = [sample["hr"] for sample in samples if sample["hr"] is not None and sample["hr"] > 0]
    title = _activity_title(filename)
    return {
        "title": title,
        "started_at": started_at,
        "sport": "CYCLING",
        "duration_minutes": round(duration / 60, 2),
        "distance_km": round(float(values["total_distance"]) / 1000, 3) if values.get("total_distance") is not None else None,
        "average_power": _number(values.get("avg_power")) or (round(mean(power_values), 2) if power_values else None),
        "normalized_power": round(normalized_power, 2) if normalized_power is not None else None,
        "average_heart_rate": _number(values.get("avg_heart_rate")) or (round(mean(heart_values), 2) if heart_values else None),
        "intensity_factor": _number(values.get("intensity_factor")),
        "tss": _number(values.get("training_stress_score")),
        "aerobic_decoupling": aerobic_decoupling,
        "notes": None,
        "_import_warnings": (
            {"aerobic_decoupling": decoupling_warning}
            if decoupling_warning
            else {}
        ),
    }


def preview_activity_file(
    content: bytes,
    filename: str,
    ftp: float | None = None,
) -> tuple[dict, str, dict[str, str]]:
    if not content:
        raise ValueError("El archivo está vacío.")
    if len(content) > MAX_ACTIVITY_FILE_BYTES:
        raise ValueError("El archivo supera el límite de 20 MB.")
    suffix = Path(filename).suffix.lower()
    if suffix == ".tcx":
        activity = parse_tcx(content, filename)
    elif suffix == ".fit":
        activity = parse_fit(content, filename)
    else:
        raise ValueError("Formato no compatible. Utiliza un archivo FIT o TCX.")
    warnings = _missing_source_warnings(activity)
    return (
        _complete_power_metrics(activity, ftp, warnings),
        sha256(content).hexdigest(),
        warnings,
    )
