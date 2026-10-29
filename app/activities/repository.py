from datetime import date, datetime
from uuid import UUID

from sqlalchemy import delete, func, select
from sqlalchemy.orm import Session

from app.database.models import ActivityRecord, PlannedWeek, PlannedWorkout, SeasonPlan


def list_for_user(
    db: Session, user_id: UUID, start: datetime | None, end: datetime | None, limit: int, offset: int
) -> tuple[list[ActivityRecord], int]:
    conditions = [ActivityRecord.user_id == user_id, ActivityRecord.external_status == "ACTIVE"]
    if start is not None:
        conditions.append(ActivityRecord.started_at >= start)
    if end is not None:
        conditions.append(ActivityRecord.started_at < end)
    query = select(ActivityRecord).where(*conditions).order_by(ActivityRecord.started_at.desc()).limit(limit).offset(offset)
    total = db.scalar(select(func.count()).select_from(ActivityRecord).where(*conditions)) or 0
    return list(db.scalars(query)), total


def get_by_id_for_user(db: Session, activity_id: UUID, user_id: UUID) -> ActivityRecord | None:
    return db.scalar(
        select(ActivityRecord).where(
            ActivityRecord.id == activity_id,
            ActivityRecord.user_id == user_id,
            ActivityRecord.external_status == "ACTIVE",
        )
    )


def get_workout_for_user(
    db: Session,
    planned_workout_id: UUID,
    user_id: UUID,
) -> PlannedWorkout | None:
    return db.scalar(
        select(PlannedWorkout)
        .join(PlannedWeek)
        .join(SeasonPlan)
        .where(
            PlannedWorkout.id == planned_workout_id,
            SeasonPlan.user_id == user_id,
        )
    )


def list_workouts_for_user_on_date(
    db: Session,
    user_id: UUID,
    scheduled_date: date,
) -> list[tuple[PlannedWorkout, UUID | None]]:
    rows = db.execute(
        select(PlannedWorkout, ActivityRecord.id)
        .join(PlannedWeek)
        .join(SeasonPlan)
        .outerjoin(
            ActivityRecord,
            (ActivityRecord.planned_workout_id == PlannedWorkout.id)
            & (ActivityRecord.external_status == "ACTIVE"),
        )
        .where(
            SeasonPlan.user_id == user_id,
            PlannedWorkout.scheduled_date == scheduled_date,
        )
        .order_by(PlannedWorkout.position)
    ).all()
    return [(workout, activity_id) for workout, activity_id in rows]


def get_activity_linked_to_workout(
    db: Session,
    planned_workout_id: UUID,
    excluding_activity_id: UUID | None = None,
) -> ActivityRecord | None:
    query = select(ActivityRecord).where(
        ActivityRecord.planned_workout_id == planned_workout_id,
        ActivityRecord.external_status == "ACTIVE",
    )
    if excluding_activity_id is not None:
        query = query.where(ActivityRecord.id != excluding_activity_id)
    return db.scalar(query)


def get_import_by_fingerprint(
    db: Session,
    user_id: UUID,
    fingerprint: str,
) -> ActivityRecord | None:
    return db.scalar(
        select(ActivityRecord).where(
            ActivityRecord.user_id == user_id,
            ActivityRecord.source == "FILE_IMPORT",
            ActivityRecord.external_source_id == fingerprint,
        )
    )


def create_for_user(db: Session, user_id: UUID, data: dict) -> ActivityRecord:
    activity = ActivityRecord(user_id=user_id, source="MANUAL", **data)
    db.add(activity)
    db.commit()
    db.refresh(activity)
    return activity


def update_for_user(db: Session, activity: ActivityRecord, data: dict) -> ActivityRecord:
    for key, value in data.items():
        setattr(activity, key, value)
    db.commit()
    db.refresh(activity)
    return activity


def delete_for_user(db: Session, activity: ActivityRecord) -> None:
    db.delete(activity)
    db.commit()
