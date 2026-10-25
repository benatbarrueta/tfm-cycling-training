from uuid import UUID
from zoneinfo import ZoneInfo

from sqlalchemy.orm import Session

from app.activities import repository
from app.activities.schemas import ActivityCreate, ActivityUpdate
from app.database.models import ActivityRecord


def create(db: Session, user_id: UUID, payload: ActivityCreate) -> ActivityRecord:
    return repository.create_for_user(db, user_id, payload.model_dump(exclude_none=False))


def update(db: Session, user_id: UUID, activity_id: UUID, payload: ActivityUpdate) -> ActivityRecord | None:
    activity = repository.get_by_id_for_user(db, activity_id, user_id)
    if activity is None:
        return None
    return repository.update_for_user(db, activity, payload.model_dump(exclude_none=False))


def delete(db: Session, user_id: UUID, activity_id: UUID) -> bool:
    activity = repository.get_by_id_for_user(db, activity_id, user_id)
    if activity is None:
        return False
    repository.delete_for_user(db, activity)
    return True


def link_to_workout(
    db: Session,
    user_id: UUID,
    activity_id: UUID,
    planned_workout_id: UUID | None,
    timezone_name: str,
) -> ActivityRecord | None:
    activity = repository.get_by_id_for_user(db, activity_id, user_id)
    if activity is None:
        return None

    if planned_workout_id is None:
        activity.planned_workout_id = None
        db.commit()
        db.refresh(activity)
        return activity

    workout = repository.get_workout_for_user(db, planned_workout_id, user_id)
    if workout is None:
        raise LookupError("Planned workout not found")

    started_at = activity.started_at
    if started_at.tzinfo is None:
        started_at = started_at.replace(tzinfo=__import__("datetime").timezone.utc)
    local_date = started_at.astimezone(ZoneInfo(timezone_name)).date()
    if local_date != workout.scheduled_date:
        raise ValueError("La actividad y la sesión planificada deben pertenecer al mismo día.")

    activity.planned_workout_id = workout.id
    db.commit()
    db.refresh(activity)
    return activity
