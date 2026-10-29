from urllib.parse import urlencode

from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session

from app.api.dependencies import get_current_user
from app.core.config import Settings, get_settings
from app.database.models import User
from app.database.session import get_db
from app.integrations.crypto import TokenCipher
from app.integrations.oauth_state import create_oauth_state, validate_oauth_state
from app.integrations.repository import delete_connection, get_connection, save_strava_connection
from app.integrations.schemas import ConnectResponse, ExternalConnectionRead, IntegrationList
from app.integrations.strava import StravaClient, StravaError

router = APIRouter(prefix="/integrations")


def _strava(settings: Settings) -> StravaClient:
    return StravaClient(settings.strava_client_id, settings.strava_client_secret, settings.strava_redirect_uri)


def _cipher(settings: Settings) -> TokenCipher:
    return TokenCipher(settings.external_token_encryption_key or settings.session_secret)


def _profile_redirect(settings: Settings, result: str) -> RedirectResponse:
    return RedirectResponse(f"{settings.frontend_origin}/profile?{urlencode({'connection': result})}#connections", status_code=303)


@router.get("", response_model=IntegrationList)
def list_integrations(
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
    settings: Settings = Depends(get_settings),
) -> IntegrationList:
    connection = get_connection(db, user.id, "STRAVA")
    return IntegrationList(
        items=[
            ExternalConnectionRead(
                provider="STRAVA",
                configured=settings.strava_configured,
                connected=connection is not None and connection.status == "CONNECTED",
                status=connection.status if connection else None,
                external_display_name=connection.external_display_name if connection else None,
                connected_at=connection.connected_at if connection else None,
                last_sync_at=connection.last_sync_at if connection else None,
            )
        ]
    )


@router.post("/strava/connect", response_model=ConnectResponse)
def connect_strava(
    user: User = Depends(get_current_user),
    settings: Settings = Depends(get_settings),
) -> ConnectResponse:
    if user.is_demo:
        raise HTTPException(status_code=403, detail="Conecta tu cuenta personal para utilizar integraciones externas.")
    if not settings.strava_configured:
        raise HTTPException(status_code=503, detail="La conexión con Strava aún no está configurada.")
    state_value = create_oauth_state(user.id, settings.session_secret)
    return ConnectResponse(authorization_url=_strava(settings).authorization_url(state_value))


@router.get("/strava/callback")
def strava_callback(
    state_value: str = Query(alias="state"),
    code: str | None = None,
    scope: str | None = None,
    error: str | None = None,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
    settings: Settings = Depends(get_settings),
) -> RedirectResponse:
    if not validate_oauth_state(state_value, user.id, settings.session_secret):
        return _profile_redirect(settings, "strava-invalid-state")
    if error or not code:
        return _profile_redirect(settings, "strava-cancelled")
    try:
        authorization = _strava(settings).exchange_code(code, scope)
        save_strava_connection(db, user.id, authorization, _cipher(settings))
    except (StravaError, ValueError):
        return _profile_redirect(settings, "strava-error")
    return _profile_redirect(settings, "strava-success")


@router.delete("/strava", status_code=status.HTTP_204_NO_CONTENT)
def disconnect_strava(
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
    settings: Settings = Depends(get_settings),
) -> None:
    connection = get_connection(db, user.id, "STRAVA")
    if connection is None:
        return
    try:
        _strava(settings).deauthorize(_cipher(settings).decrypt(connection.access_token_encrypted))
    except (StravaError, ValueError):
        # Local disconnection must remain possible even when Strava is unavailable.
        pass
    delete_connection(db, connection)
