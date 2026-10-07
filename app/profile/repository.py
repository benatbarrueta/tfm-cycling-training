from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.database.models import CyclistProfile, utc_now
from app.profile.schemas import CyclistProfileUpsert


def get_profile(db: Session, user_id: UUID) -> CyclistProfile | None:
    return db.scalar(select(CyclistProfile).where(CyclistProfile.user_id == user_id))


def upsert_profile(db: Session, user_id: UUID, payload: CyclistProfileUpsert) -> CyclistProfile:
    profile = get_profile(db, user_id)
    if profile is None:
        profile = CyclistProfile(user_id=user_id, onboarding_completed_at=utc_now())
        db.add(profile)

    profile.ftp = payload.ftp
    profile.weekly_hours = payload.weekly_hours
    profile.available_days = [day.value for day in payload.available_days]
    profile.modality = payload.modality.value
    profile.level = payload.level.value
    profile.objective = payload.objective.value
    profile.target_date = payload.target_date
    profile.timezone = payload.timezone
    db.commit()
    db.refresh(profile)
    return profile
