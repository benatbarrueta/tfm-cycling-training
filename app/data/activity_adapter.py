from pathlib import Path
from datetime import datetime

from app.data.goldencheetah import metric, signed_metric
from app.data.response_audit import read_athlete_summary
from app.models.activity import Activity

def activity_from_goldencheetah_ride(
    ride: dict,
) -> Activity | None:
    """Convierte una actividad Bike válida de GoldenCheetah al dominio."""
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

    if (
        duration_seconds is None
        or duration_seconds < 60
        or average_power is None
        or average_power <= 0
        or normalized_power is None
        or normalized_power <= 0
    ):
        return None

    return Activity(
        date=activity_date,
        duration_minutes=round(duration_seconds / 60),
        average_power=average_power,
        normalized_power=normalized_power,
        intensity_factor=metric(
            metrics.get("coggan_if")
        ),
        tss=metric(
            metrics.get("coggan_tss")
        ),
        aerobic_decoupling=signed_metric(
            metrics.get("aerobic_decoupling")
        ),
    )

def activities_from_goldencheetah_data(
    data: dict,
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

    activities = []
    activities_by_datetime = {}

    skipped_non_bike = 0
    skipped_invalid = 0
    duplicate_activities = 0

    for ride in rides:
        if ride.get("sport") != "Bike":
            skipped_non_bike += 1
            continue

        activity = activity_from_goldencheetah_ride(
            ride
        )

        if activity is None:
            skipped_invalid += 1
            continue

        ride_datetime = ride["date"]

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

def load_goldencheetah_activities(
    path: str | Path,
) -> tuple[list[Activity], dict]:
    """Lee un resumen JSON o ZIP y lo convierte en actividades del dominio."""
    data = read_athlete_summary(path)

    activities, audit = (
        activities_from_goldencheetah_data(
            data
        )
    )

    audit["source"] = str(Path(path))

    return activities, audit
