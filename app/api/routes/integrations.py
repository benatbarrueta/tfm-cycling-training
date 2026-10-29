from datetime import date, datetime, timedelta, timezone
from urllib.parse import urlencode
from zoneinfo import ZoneInfo

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
from app.integrations.schemas import (
    ConnectResponse,
    ExternalConnectionRead,
    IntegrationList,
    StravaActivityList,
    StravaSyncRequest,
    StravaSyncResult,
)
from app.integrations.service import (
    list_strava_activities,
    sync_incremental_strava_activities,
    sync_strava_activities,
)
from app.integrations.strava import (
    StravaAuthenticationError,
    StravaClient,
    StravaError,
    StravaRateLimitError,
    StravaUnavailableError,
)
from app.profile.repository import get_profile

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
                sync_start_date=connection.sync_start_date if connection else None,
                sync_enabled=connection.sync_enabled if connection else False,
                sync_status=connection.sync_status if connection else "NOT_CONFIGURED",
                sync_total=connection.sync_total if connection else 0,
                sync_imported=connection.sync_imported if connection else 0,
                sync_skipped=connection.sync_skipped if connection else 0,
                sync_failed=connection.sync_failed if connection else 0,
                sync_last_error=connection.sync_last_error if connection else None,
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


@router.get("/strava/activities", response_model=StravaActivityList)
def list_available_strava_activities(
    start: date | None = None,
    end: date | None = None,
    page: int = Query(default=1, ge=1),
    limit: int = Query(default=20, ge=1, le=100),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
    settings: Settings = Depends(get_settings),
) -> StravaActivityList:
    connection = get_connection(db, user.id, "STRAVA")
    if connection is None or connection.status != "CONNECTED":
        raise HTTPException(status_code=409, detail="Conecta de nuevo tu cuenta de Strava para consultar actividades.")
    if not ({"activity:read", "activity:read_all"} & set(connection.granted_scopes)):
        raise HTTPException(status_code=403, detail="La conexión de Strava no tiene permiso para leer actividades.")

    profile = get_profile(db, user.id)
    timezone_name = profile.timezone if profile is not None else "UTC"
    today = datetime.now(ZoneInfo(timezone_name)).date()
    range_end = end or today
    range_start = start or (range_end - timedelta(days=29))
    if range_start > range_end:
        raise HTTPException(status_code=422, detail="La fecha inicial debe ser anterior o igual a la fecha final.")
    try:
        return list_strava_activities(
            db,
            user.id,
            connection,
            _strava(settings),
            _cipher(settings),
            start=range_start,
            end=range_end,
            timezone_name=timezone_name,
            page=page,
            limit=limit,
        )
    except StravaAuthenticationError as exc:
        raise HTTPException(status_code=401, detail="La autorización de Strava ha caducado. Vuelve a conectar tu cuenta.") from exc
    except StravaRateLimitError as exc:
        raise HTTPException(status_code=429, detail="Strava ha alcanzado temporalmente su límite de consultas. Inténtalo más tarde.") from exc
    except StravaUnavailableError as exc:
        raise HTTPException(status_code=503, detail="Strava no está disponible en este momento. Inténtalo de nuevo más tarde.") from exc
    except (StravaError, ValueError) as exc:
        raise HTTPException(status_code=502, detail="No se han podido consultar las actividades de Strava.") from exc


@router.post("/strava/sync", response_model=StravaSyncResult)
def start_strava_sync(
    payload: StravaSyncRequest,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
    settings: Settings = Depends(get_settings),
) -> StravaSyncResult:
    connection = get_connection(db, user.id, "STRAVA")
    if connection is None or connection.status != "CONNECTED":
        raise HTTPException(status_code=409, detail="Conecta de nuevo tu cuenta de Strava para sincronizar actividades.")
    profile = get_profile(db, user.id)
    if profile is None:
        raise HTTPException(status_code=409, detail="Completa tu perfil antes de sincronizar actividades.")
    today = datetime.now(ZoneInfo(profile.timezone)).date()
    if payload.start_date > today:
        raise HTTPException(status_code=422, detail="La fecha inicial no puede estar en el futuro.")
    if connection.sync_status in {"PENDING", "RUNNING"}:
        raise HTTPException(status_code=409, detail="Ya hay una sincronización de Strava en curso.")
    try:
        return sync_strava_activities(
            db,
            user.id,
            connection,
            _strava(settings),
            _cipher(settings),
            start_date=payload.start_date,
            timezone_name=profile.timezone,
            ftp=profile.ftp,
        )
    except StravaAuthenticationError as exc:
        raise HTTPException(status_code=401, detail="La autorización de Strava ha caducado. Vuelve a conectar tu cuenta.") from exc
    except StravaRateLimitError as exc:
        raise HTTPException(status_code=429, detail="Strava ha alcanzado temporalmente su límite de consultas. Inténtalo más tarde.") from exc
    except StravaUnavailableError as exc:
        raise HTTPException(status_code=503, detail="Strava no está disponible en este momento. Inténtalo de nuevo más tarde.") from exc
    except (StravaError, ValueError) as exc:
        raise HTTPException(status_code=502, detail="No se ha podido completar la sincronización con Strava.") from exc


@router.post("/strava/sync/incremental", response_model=StravaSyncResult)
def sync_strava_incrementally(
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
    settings: Settings = Depends(get_settings),
) -> StravaSyncResult:
    connection = get_connection(db, user.id, "STRAVA")
    profile = get_profile(db, user.id)
    today = datetime.now(ZoneInfo(profile.timezone if profile else "UTC")).date()
    fallback = StravaSyncResult(
        status="NOT_CONFIGURED",
        total=0,
        imported=0,
        skipped=0,
        failed=0,
        start_date=today,
    )
    if (
        connection is None
        or connection.status != "CONNECTED"
        or not connection.sync_enabled
        or connection.sync_start_date is None
        or profile is None
    ):
        return fallback
    now = datetime.now(timezone.utc).replace(tzinfo=None)
    last_sync_at = connection.last_sync_at
    if last_sync_at is not None and last_sync_at.tzinfo is not None:
        last_sync_at = last_sync_at.astimezone(timezone.utc).replace(tzinfo=None)
    if last_sync_at is not None and now - last_sync_at < timedelta(minutes=5):
        return fallback.model_copy(
            update={"status": "SKIPPED_RECENT", "start_date": connection.sync_start_date}
        )
    if connection.sync_status in {"PENDING", "RUNNING"}:
        return fallback.model_copy(
            update={"status": "SKIPPED_RUNNING", "start_date": connection.sync_start_date}
        )
    try:
        return sync_incremental_strava_activities(
            db,
            user.id,
            connection,
            _strava(settings),
            _cipher(settings),
            timezone_name=profile.timezone,
            ftp=profile.ftp,
        )
    except StravaAuthenticationError as exc:
        raise HTTPException(status_code=401, detail="La autorización de Strava ha caducado. Vuelve a conectar tu cuenta.") from exc
    except StravaRateLimitError as exc:
        raise HTTPException(status_code=429, detail="Strava ha alcanzado temporalmente su límite de consultas. Inténtalo más tarde.") from exc
    except StravaUnavailableError as exc:
        raise HTTPException(status_code=503, detail="Strava no está disponible en este momento. Inténtalo de nuevo más tarde.") from exc
    except (StravaError, ValueError) as exc:
        raise HTTPException(status_code=502, detail="No se ha podido actualizar el calendario desde Strava.") from exc
