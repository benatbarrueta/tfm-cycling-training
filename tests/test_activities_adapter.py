from datetime import datetime
from uuid import uuid4

from app.activities.adapter import to_domain_activity
from app.database.models import ActivityRecord


def test_persisted_activity_converts_to_domain_using_profile_timezone():
    record = ActivityRecord(
        id=uuid4(),
        user_id=uuid4(),
        title="Ride",
        started_at=datetime(2026, 10, 7, 22, 30),
        sport="CYCLING",
        duration_minutes=90,
        average_power=180,
        normalized_power=190,
        intensity_factor=0.8,
        tss=70,
        aerobic_decoupling=-1.5,
        source="MANUAL",
    )

    activity = to_domain_activity(record, "Europe/Madrid")

    assert activity.date.isoformat() == "2026-10-08"
    assert activity.duration_minutes == 90
    assert activity.normalized_power == 190
    assert activity.aerobic_decoupling == -1.5
