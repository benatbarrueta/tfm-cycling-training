from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.dependencies import get_current_user
from app.core.config import Settings, get_settings
from app.database.models import CyclistProfile, User
from app.database.session import get_db
from app.profile.repository import get_profile
from app.season.schemas import SeasonPlanCreate, SeasonPlanRead
from app.season.service import create_plan, get_plan

router = APIRouter(prefix="/season-plans")


@router.post("", response_model=SeasonPlanRead, status_code=status.HTTP_201_CREATED)
def create_season_plan(
    payload: SeasonPlanCreate,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
) -> SeasonPlanRead:
    profile = get_profile(db, user.id)
    if profile is None:
        raise HTTPException(status_code=422, detail="Completa el perfil ciclista antes de crear un plan.")
    try:
        return create_plan(db, user, profile, payload.name, settings)
    except RuntimeError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    except ValueError as exc:
        db.rollback()
        raise HTTPException(status_code=422, detail=str(exc)) from exc


@router.get("/current", response_model=SeasonPlanRead)
def current_plan(user: User = Depends(get_current_user), db: Session = Depends(get_db)) -> SeasonPlanRead:
    plan = get_plan(db, user.id)
    if plan is None:
        raise HTTPException(status_code=404, detail="No hay un plan activo.")
    return plan


@router.get("/{plan_id}", response_model=SeasonPlanRead)
def read_plan(plan_id: UUID, user: User = Depends(get_current_user), db: Session = Depends(get_db)) -> SeasonPlanRead:
    plan = get_plan(db, user.id, plan_id)
    if plan is None:
        raise HTTPException(status_code=404, detail="Plan no encontrado.")
    return plan
