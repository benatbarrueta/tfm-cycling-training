from datetime import date
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.dependencies import get_current_user
from app.core.config import Settings, get_settings
from app.database.models import CyclistProfile, User
from app.database.session import get_db
from app.profile.repository import get_profile
from app.season.schemas import (
    AdvanceSeasonPlanRead,
    AdaptationEventRead,
    SeasonPlanCreate,
    SeasonPlanRead,
    WeeklyReviewRead,
    WeeklyReviewPreviewRead,
)
from app.season.service import (
    advance_plan,
    create_plan,
    get_plan,
    list_adaptations,
    list_plans,
    preview_week_review,
    recalculate_week_review,
)

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


@router.get("", response_model=list[SeasonPlanRead])
def read_plans(
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> list[SeasonPlanRead]:
    return list_plans(db, user.id)


@router.get("/current/weekly-review-preview", response_model=WeeklyReviewPreviewRead)
def current_week_review_preview(
    reference_date: date | None = None,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
) -> WeeklyReviewPreviewRead:
    if reference_date is not None and settings.app_env != "development":
        raise HTTPException(status_code=404, detail="Recurso no encontrado.")
    profile = get_profile(db, user.id)
    if profile is None:
        raise HTTPException(status_code=422, detail="Completa el perfil ciclista.")
    try:
        return preview_week_review(db, user.id, profile, reference=reference_date)
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


@router.post("/current/advance", response_model=AdvanceSeasonPlanRead)
def advance_current_plan(
    reference_date: date | None = None,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
) -> AdvanceSeasonPlanRead:
    if reference_date is not None and settings.app_env != "development":
        raise HTTPException(status_code=404, detail="Recurso no encontrado.")
    profile = get_profile(db, user.id)
    if profile is None:
        raise HTTPException(status_code=422, detail="Completa el perfil ciclista.")
    try:
        return advance_plan(db, user, profile, settings, reference=reference_date)
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except RuntimeError as exc:
        db.rollback()
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    except ValueError as exc:
        db.rollback()
        raise HTTPException(status_code=422, detail=str(exc)) from exc


@router.post("/current/weeks/{week_id}/review/recalculate", response_model=WeeklyReviewRead)
def recalculate_current_week_review(
    week_id: UUID,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> WeeklyReviewRead:
    profile = get_profile(db, user.id)
    if profile is None:
        raise HTTPException(status_code=422, detail="Completa el perfil ciclista.")
    try:
        return recalculate_week_review(db, user.id, profile, week_id)
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


@router.get("/{plan_id}", response_model=SeasonPlanRead)
def read_plan(plan_id: UUID, user: User = Depends(get_current_user), db: Session = Depends(get_db)) -> SeasonPlanRead:
    plan = get_plan(db, user.id, plan_id)
    if plan is None:
        raise HTTPException(status_code=404, detail="Plan no encontrado.")
    return plan


@router.get("/{plan_id}/adaptations", response_model=list[AdaptationEventRead])
def read_adaptations(
    plan_id: UUID,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> list[AdaptationEventRead]:
    try:
        return list_adaptations(db, user.id, plan_id)
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
