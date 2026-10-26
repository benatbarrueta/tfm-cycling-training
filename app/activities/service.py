from datetime import date, timezone
from uuid import UUID
from zoneinfo import ZoneInfo

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.activities import repository
from app.activities.schemas import ActivityCreate, ActivityUpdate
from app.database.models import ActivityRecord


def create(db: Session, user_id: UUID, payload: ActivityCreate) -> ActivityRecord:
    return repository.create_for_user(db, user_id, payload.model_dump(exclude_none=False))


def _local_activity_date(activity: ActivityRecord, timezone_name: str) -> date:
    started_at = activity.started_at
    if started_at.tzinfo is None:
        started_at = started_at.replace(tzinfo=timezone.utc)
    return started_at.astimezone(ZoneInfo(timezone_name)).date()


def update(
    db: Session,
    user_id: UUID,
    activity_id: UUID,
    payload: ActivityUpdate,
    timezone_name: str,
) -> ActivityRecord | None:
    activity = repository.get_by_id_for_user(db, activity_id, user_id)
    if activity is None:
        return None

    if activity.planned_workout_id is not None:
        workout = repository.get_workout_for_user(
            db,
            activity.planned_workout_id,
            user_id,
        )
        started_at = payload.started_at
        if started_at.tzinfo is None:
            started_at = started_at.replace(tzinfo=timezone.utc)
        local_date = started_at.astimezone(ZoneInfo(timezone_name)).date()
        if workout is not None and local_date != workout.scheduled_date:
            raise ValueError(
                "Selecciona una sesión planificada del nuevo día "
                "o guarda la actividad como adicional."
            )
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

    local_date = _local_activity_date(activity, timezone_name)
    if local_date != workout.scheduled_date:
        raise ValueError("La actividad y la sesión planificada deben pertenecer al mismo día.")

    occupied_by = repository.get_activity_linked_to_workout(
        db,
        workout.id,
        excluding_activity_id=activity.id,
    )
    if occupied_by is not None:
        raise ValueError("Esta sesión ya está vinculada a otra actividad.")

    activity.planned_workout_id = workout.id
    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise ValueError("Esta sesión ya está vinculada a otra actividad.") from exc
    db.refresh(activity)
    return activity


def available_workouts(
    db: Session,
    user_id: UUID,
    scheduled_date: date,
) -> list[dict]:
    return [
        {
            "id": workout.id,
            "scheduled_date": workout.scheduled_date,
            "workout_type": workout.workout_type,
            "duration_minutes": workout.duration_minutes,
            "estimated_tss": workout.estimated_tss,
            "target_tss": workout.target_tss,
            "already_linked": activity_id is not None,
            "linked_activity_id": activity_id,
        }
        for workout, activity_id in repository.list_workouts_for_user_on_date(
            db,
            user_id,
            scheduled_date,
        )
    ]
