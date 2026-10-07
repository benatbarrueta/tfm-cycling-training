from fastapi import APIRouter, Cookie, Depends, HTTPException, Request, Response, status
from sqlalchemy.orm import Session

from app.api.dependencies import get_current_user
from app.auth.google import GoogleTokenError, GoogleTokenVerifier
from app.auth.schemas import GoogleCredential, PublicUser
from app.auth.sessions import create_session, revoke_session
from app.core.config import Settings, get_settings
from app.database.models import User
from app.database.session import get_db
from app.repositories.user_repository import IdentityConflictError, get_or_create_demo_user, upsert_google_user

router = APIRouter(prefix="/auth")


def public_user(user: User) -> PublicUser:
    return PublicUser.model_validate(user)


@router.post("/google", response_model=PublicUser)
def login_google(
    payload: GoogleCredential,
    response: Response,
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
) -> PublicUser:
    try:
        identity = GoogleTokenVerifier(settings.google_client_id).verify(payload.credential)
        user = upsert_google_user(db, identity)
    except IdentityConflictError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    except GoogleTokenError as exc:
        raise HTTPException(status_code=401, detail="Invalid authentication credentials") from exc
    token = create_session(db, user, settings)
    response.set_cookie(
        settings.session_cookie_name,
        token,
        httponly=True,
        secure=settings.is_production,
        samesite="lax",
        path="/",
        max_age=settings.session_ttl_days * 86400,
    )
    return public_user(user)


@router.post("/demo", response_model=PublicUser)
def login_demo(
    response: Response,
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
) -> PublicUser:
    if settings.app_env != "development":
        raise HTTPException(status_code=404, detail="Not found")
    user = get_or_create_demo_user(db)
    token = create_session(db, user, settings)
    response.set_cookie(settings.session_cookie_name, token, httponly=True, secure=False, samesite="lax", path="/", max_age=settings.session_ttl_days * 86400)
    return public_user(user)


@router.get("/me", response_model=PublicUser)
def get_me(user: User = Depends(get_current_user)) -> PublicUser:
    return public_user(user)


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
def logout(
    request: Request,
    response: Response,
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
) -> None:
    session_token = request.cookies.get(settings.session_cookie_name)
    revoke_session(db, session_token, settings.session_secret)
    response.delete_cookie(settings.session_cookie_name, path="/")
