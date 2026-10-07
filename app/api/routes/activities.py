from datetime import datetime
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from sqlalchemy.orm import Session

from app.activities import repository, service
from app.activities.schemas import ActivityCreate, ActivityListResponse, ActivityRead, ActivityUpdate
from app.api.dependencies import get_current_user
from app.database.models import User
from app.database.session import get_db

router = APIRouter(prefix="/activities")


@router.get("", response_model=ActivityListResponse)
def list_activities(
    start: datetime | None = None,
    end: datetime | None = None,
    limit: int = Query(default=50, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> ActivityListResponse:
    if start is not None and (start.tzinfo is None or start.utcoffset() is None):
        raise HTTPException(status_code=422, detail="start debe incluir zona horaria")
    if end is not None and (end.tzinfo is None or end.utcoffset() is None):
        raise HTTPException(status_code=422, detail="end debe incluir zona horaria")
    if start is not None and end is not None and start >= end:
        raise HTTPException(status_code=422, detail="start debe ser anterior a end")
    items, total = repository.list_for_user(
        db, user.id,
        start.astimezone(__import__("datetime").timezone.utc).replace(tzinfo=None) if start else None,
        end.astimezone(__import__("datetime").timezone.utc).replace(tzinfo=None) if end else None,
        limit, offset,
    )
    return ActivityListResponse(items=items, total=total, limit=limit, offset=offset)


@router.post("", response_model=ActivityRead, status_code=status.HTTP_201_CREATED)
def create_activity(payload: ActivityCreate, user: User = Depends(get_current_user), db: Session = Depends(get_db)) -> ActivityRead:
    return service.create(db, user.id, payload)


@router.get("/{activity_id}", response_model=ActivityRead)
def get_activity(activity_id: UUID, user: User = Depends(get_current_user), db: Session = Depends(get_db)) -> ActivityRead:
    activity = repository.get_by_id_for_user(db, activity_id, user.id)
    if activity is None:
        raise HTTPException(status_code=404, detail="Activity not found")
    return activity


@router.put("/{activity_id}", response_model=ActivityRead)
def update_activity(activity_id: UUID, payload: ActivityUpdate, user: User = Depends(get_current_user), db: Session = Depends(get_db)) -> ActivityRead:
    activity = service.update(db, user.id, activity_id, payload)
    if activity is None:
        raise HTTPException(status_code=404, detail="Activity not found")
    return activity


@router.delete("/{activity_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_activity(activity_id: UUID, user: User = Depends(get_current_user), db: Session = Depends(get_db)) -> Response:
    if not service.delete(db, user.id, activity_id):
        raise HTTPException(status_code=404, detail="Activity not found")
    return Response(status_code=status.HTTP_204_NO_CONTENT)
