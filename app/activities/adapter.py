from zoneinfo import ZoneInfo

from app.database.models import ActivityRecord
from app.models.activity import Activity


def to_domain_activity(activity: ActivityRecord, timezone_name: str = "Europe/Madrid") -> Activity:
    """Convert persisted data to the training-domain activity model."""
    local_date = activity.started_at.replace(tzinfo=ZoneInfo("UTC")).astimezone(
        ZoneInfo(timezone_name)
    ).date()
    return Activity(
        date=local_date,
        duration_minutes=round(activity.duration_minutes),
        average_power=activity.average_power,
        normalized_power=activity.normalized_power,
        intensity_factor=activity.intensity_factor,
        tss=activity.tss,
        aerobic_decoupling=activity.aerobic_decoupling,
    )
