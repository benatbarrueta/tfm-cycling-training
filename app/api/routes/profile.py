from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.dependencies import get_current_user
from app.database.models import User
from app.database.session import get_db
from app.profile.repository import get_profile, upsert_profile
from app.profile.schemas import CyclistProfileRead, CyclistProfileUpsert

router = APIRouter(prefix="/profile")


@router.get("", response_model=CyclistProfileRead)
def read_profile(
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> CyclistProfileRead:
    profile = get_profile(db, user.id)
    if profile is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Cyclist profile not found")
    return profile


@router.put("", response_model=CyclistProfileRead)
def save_profile(
    payload: CyclistProfileUpsert,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> CyclistProfileRead:
    return upsert_profile(db, user.id, payload)
