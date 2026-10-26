from __future__ import annotations

from datetime import datetime, timezone
from hashlib import sha256
from io import BytesIO
from pathlib import Path
import re
from statistics import mean
from xml.etree import ElementTree

from app.data.response_audit import build_activity_response


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


def _decoupling(samples: list[dict]) -> float | None:
    try:
        response = build_activity_response(samples)
    except ValueError:
        return None
    return None if response is None else float(response["aerobic_decoupling"])


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
        {"secs": (timestamp - started_at).total_seconds(), "watts": watts, "hr": heart_rate}
        for timestamp, watts, heart_rate in point_rows
        if watts is not None and heart_rate is not None and heart_rate > 0
    ]

    def named_metric(*names: str) -> float | None:
        for name in names:
            value = _number(_first_text(activity, name))
            if value is not None:
                return value
        return None

    title = _activity_title(filename)
    return {
        "title": title,
        "started_at": started_at,
        "sport": "CYCLING",
        "duration_minutes": round(duration_seconds / 60, 2),
        "distance_km": round(max(distances) / 1000, 3) if distances else None,
        "average_power": round(mean(power_values), 2) if power_values else None,
        "normalized_power": named_metric("NormalizedPower", "NormalizedBikePower"),
        "average_heart_rate": round(mean(heart_values), 2) if heart_values else None,
        "intensity_factor": named_metric("IntensityFactor"),
        "tss": named_metric("TrainingStressScore", "TSS"),
        "aerobic_decoupling": _decoupling(signal),
        "notes": None,
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
    for record in records:
        row = record.get_values()
        timestamp = row.get("timestamp")
        if not isinstance(timestamp, datetime):
            continue
        if timestamp.tzinfo is None:
            timestamp = timestamp.replace(tzinfo=timezone.utc)
        samples.append({
            "secs": (timestamp - started_at).total_seconds(),
            "watts": _number(row.get("power")),
            "hr": _number(row.get("heart_rate")),
        })

    duration = _number(values.get("total_timer_time") or values.get("total_elapsed_time"))
    if duration is None or duration <= 0:
        raise ValueError("No se ha podido obtener la duración de la actividad.")
    title = _activity_title(filename)
    return {
        "title": title,
        "started_at": started_at,
        "sport": "CYCLING",
        "duration_minutes": round(duration / 60, 2),
        "distance_km": round(float(values["total_distance"]) / 1000, 3) if values.get("total_distance") is not None else None,
        "average_power": _number(values.get("avg_power")),
        "normalized_power": _number(values.get("normalized_power")),
        "average_heart_rate": _number(values.get("avg_heart_rate")),
        "intensity_factor": _number(values.get("intensity_factor")),
        "tss": _number(values.get("training_stress_score")),
        "aerobic_decoupling": _decoupling(samples),
        "notes": None,
    }


def preview_activity_file(content: bytes, filename: str) -> tuple[dict, str]:
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
    return activity, sha256(content).hexdigest()
