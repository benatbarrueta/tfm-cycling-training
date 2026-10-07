from uuid import UUID

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
