from pathlib import Path
from datetime import datetime

from app.data.goldencheetah import metric, signed_metric
from app.data.response_audit import (
    collect_athlete_decoupling_comparisons,
    is_eligible_decoupling_response,
    read_athlete_summary,
)
from app.models.activity import Activity

def activity_from_goldencheetah_ride(
    ride: dict,
    *,
    aerobic_decoupling: float | None = None,
) -> Activity | None:
    """Convierte una actividad Bike utilizable de GoldenCheetah."""
    if ride.get("sport") != "Bike":
        return None

    try:
        activity_date = datetime.strptime(
            ride["date"],
            "%Y/%m/%d %H:%M:%S UTC",
        ).date()
    except (KeyError, TypeError, ValueError):
        return None

    metrics = ride.get("METRICS", {})

    duration_seconds = metric(
        metrics.get("workout_time")
    )
    average_power = metric(
        metrics.get("average_power")
    )
    normalized_power = metric(
        metrics.get("coggan_np")
    )
    intensity_factor = metric(
        metrics.get("coggan_if")
    )
    tss = metric(
        metrics.get("coggan_tss")
    )

    can_calculate_tss = (
        duration_seconds is not None
        and duration_seconds >= 60
        and normalized_power is not None
        and normalized_power > 0
    )

    if tss is None and not can_calculate_tss:
        return None

    duration_minutes = (
        round(duration_seconds / 60)
        if duration_seconds is not None
        and duration_seconds >= 60
        else None
    )

    return Activity(
        date=activity_date,
        duration_minutes=duration_minutes,
        average_power=average_power,
        normalized_power=normalized_power,
        intensity_factor=intensity_factor,
        tss=tss,
        aerobic_decoupling=aerobic_decoupling,
    )

def activities_from_goldencheetah_data(
    data: dict,
    *,
    calculated_responses: dict[str, float] | None = None,
) -> tuple[list[Activity], dict]:
    """Convierte el resumen completo de un atleta y genera una auditoría."""
    athlete_id = str(
        data.get("ATHLETE", {}).get("id", "")
    ).strip("{}")

    if not athlete_id:
        raise ValueError(
            "El resumen no contiene un identificador de atleta."
        )

    rides = data.get("RIDES", [])

    if not isinstance(rides, list):
        raise ValueError(
            "Las actividades del resumen deben ser una lista."
        )

    if calculated_responses is None:
        calculated_responses = {}

    activities = []
    activities_by_datetime = {}

    skipped_non_bike = 0
    skipped_invalid = 0
    duplicate_activities = 0

    for ride in rides:
        if ride.get("sport") != "Bike":
            skipped_non_bike += 1
            continue

        ride_datetime = ride.get("date")

        activity = activity_from_goldencheetah_ride(
            ride,
            aerobic_decoupling=(
                calculated_responses.get(
                    ride_datetime
                )
            ),
        )

        if activity is None:
            skipped_invalid += 1
            continue

        existing_activity = activities_by_datetime.get(
            ride_datetime
        )

        if existing_activity is not None:
            if activity != existing_activity:
                raise ValueError(
                    "Existen actividades diferentes "
                    f"con la fecha y hora {ride_datetime}."
                )

            duplicate_activities += 1
            continue

        activities_by_datetime[ride_datetime] = activity
        activities.append(activity)

    activities.sort(
        key=lambda activity: activity.date
    )

    audit = {
        "athlete_id": athlete_id,
        "source_activities": len(rides),
        "imported_activities": len(activities),
        "skipped_non_bike": skipped_non_bike,
        "skipped_invalid": skipped_invalid,
        "duplicate_activities": duplicate_activities,
    }

    return activities, audit

def build_calculated_response_lookup(
    comparisons: list[dict],
) -> dict[str, float]:
    """Relaciona cada actividad elegible con su respuesta calculada."""
    responses = {}

    for comparison in comparisons:
        if not is_eligible_decoupling_response(
            comparison
        ):
            continue

        ride_date = comparison["ride_date"]
        calculated_decoupling = float(
            comparison["calculated_decoupling"]
        )

        if ride_date in responses:
            raise ValueError(
                "Existe más de una respuesta calculada "
                f"para {ride_date}."
            )

        responses[ride_date] = calculated_decoupling

    return responses

def load_goldencheetah_activities(
    path: str | Path,
) -> tuple[list[Activity], dict]:
    """Lee un resumen y adjunta respuestas calculadas cuando existe un ZIP."""
    path = Path(path)
    data = read_athlete_summary(path)

    calculated_responses = {}

    if path.suffix.lower() == ".zip":
        comparisons = (
            collect_athlete_decoupling_comparisons(
                path
            )
        )

        calculated_responses = (
            build_calculated_response_lookup(
                comparisons
            )
        )

    activities, audit = (
        activities_from_goldencheetah_data(
            data,
            calculated_responses=calculated_responses,
        )
    )

    audit["source"] = str(path)
    audit["eligible_calculated_responses"] = len(
        calculated_responses
    )

    return activities, audit
