from datetime import date, datetime, time, timedelta, timezone
from statistics import mean
from uuid import UUID
from zoneinfo import ZoneInfo

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.activities.file_import import _complete_power_metrics, _decoupling, _normalized_power
from app.activities.repository import list_workouts_for_user_on_date
from app.database.models import ActivityRecord, ExternalConnection
from app.integrations.crypto import TokenCipher
from app.integrations.repository import (
    imported_external_ids,
    mark_connection_status,
    mark_connection_synced,
    update_strava_tokens,
)
from app.integrations.schemas import StravaActivityCandidate, StravaActivityList, StravaSyncResult
from app.integrations.strava import (
    StravaAuthenticationError,
    StravaClient,
    StravaError,
    StravaRateLimitError,
    StravaUnavailableError,
)


CYCLING_TYPES = {
    "Ride",
    "MountainBikeRide",
    "GravelRide",
    "VirtualRide",
    "EBikeRide",
    "EMountainBikeRide",
}


def _utc_naive(value: datetime) -> datetime:
    if value.tzinfo is not None:
        return value.astimezone(timezone.utc).replace(tzinfo=None)
    return value


def _refresh_tokens(
    db: Session,
    connection: ExternalConnection,
    client: StravaClient,
    cipher: TokenCipher,
) -> str:
    refresh_token = cipher.decrypt(connection.refresh_token_encrypted)
    try:
        tokens = client.refresh_access_token(refresh_token)
    except StravaAuthenticationError:
        mark_connection_status(db, connection, "REAUTHORIZATION_REQUIRED")
        raise
    update_strava_tokens(db, connection, tokens, cipher)
    return tokens.access_token


def valid_access_token(
    db: Session,
    connection: ExternalConnection,
    client: StravaClient,
    cipher: TokenCipher,
) -> str:
    now = datetime.now(timezone.utc).replace(tzinfo=None)
    if _utc_naive(connection.token_expires_at) <= now + timedelta(minutes=5):
        return _refresh_tokens(db, connection, client, cipher)
    return cipher.decrypt(connection.access_token_encrypted)


def _number(value: object, divisor: float = 1.0) -> float | None:
    if value is None or isinstance(value, bool):
        return None
    try:
        return round(float(value) / divisor, 2)
    except (TypeError, ValueError):
        return None


def _candidate(activity: dict, imported: set[str]) -> StravaActivityCandidate | None:
    sport_type = str(activity.get("sport_type") or activity.get("type") or "")
    if sport_type not in CYCLING_TYPES:
        return None
    external_id = str(activity.get("id") or "")
    started_at = activity.get("start_date")
    duration_seconds = activity.get("moving_time") or activity.get("elapsed_time")
    if not external_id or not isinstance(started_at, str) or duration_seconds is None:
        return None
    try:
        parsed_start = datetime.fromisoformat(started_at.replace("Z", "+00:00"))
        duration_minutes = round(float(duration_seconds) / 60, 2)
    except (TypeError, ValueError):
        return None
    if duration_minutes <= 0:
        return None
    has_measured_power = activity.get("device_watts") is True
    return StravaActivityCandidate(
        external_id=external_id,
        name=str(activity.get("name") or "Actividad de ciclismo"),
        sport_type=sport_type,
        started_at=parsed_start,
        duration_minutes=duration_minutes,
        distance_km=_number(activity.get("distance"), 1000),
        elevation_gain_m=_number(activity.get("total_elevation_gain")),
        average_power=_number(activity.get("average_watts")) if has_measured_power else None,
        normalized_power=_number(activity.get("weighted_average_watts")) if has_measured_power else None,
        average_heart_rate=_number(activity.get("average_heartrate")),
        trainer=bool(activity.get("trainer", False)),
        commute=bool(activity.get("commute", False)),
        already_imported=external_id in imported,
    )


def list_strava_activities(
    db: Session,
    user_id: UUID,
    connection: ExternalConnection,
    client: StravaClient,
    cipher: TokenCipher,
    *,
    start: date,
    end: date,
    timezone_name: str,
    page: int,
    limit: int,
) -> StravaActivityList:
    zone = ZoneInfo(timezone_name)
    after = int(datetime.combine(start, time.min, zone).timestamp())
    before = int(datetime.combine(end + timedelta(days=1), time.min, zone).timestamp())
    access_token = valid_access_token(db, connection, client, cipher)
    try:
        raw_items = client.list_athlete_activities(
            access_token,
            after=after,
            before=before,
            page=page,
            per_page=limit,
        )
    except StravaAuthenticationError:
        access_token = _refresh_tokens(db, connection, client, cipher)
        try:
            raw_items = client.list_athlete_activities(
                access_token,
                after=after,
                before=before,
                page=page,
                per_page=limit,
            )
        except StravaAuthenticationError:
            mark_connection_status(db, connection, "REAUTHORIZATION_REQUIRED")
            raise

    visible_raw = raw_items
    ids = {str(item.get("id")) for item in visible_raw if item.get("id") is not None}
    imported = imported_external_ids(db, user_id, "STRAVA", ids)
    candidates = [candidate for item in visible_raw if (candidate := _candidate(item, imported)) is not None]
    mark_connection_synced(db, connection)
    return StravaActivityList(
        items=candidates,
        page=page,
        limit=limit,
        has_more=len(raw_items) == limit,
    )


def _stream_rows(detail: dict, streams: dict[str, list]) -> tuple[list[tuple[datetime, float | None]], list[dict]]:
    started_at = datetime.fromisoformat(str(detail["start_date"]).replace("Z", "+00:00"))
    elapsed = streams.get("time", [])
    watts = streams.get("watts", []) if detail.get("device_watts") is True else []
    heart_rates = streams.get("heartrate", [])
    power_rows: list[tuple[datetime, float | None]] = []
    paired_rows: list[dict] = []
    for index, seconds_value in enumerate(elapsed):
        try:
            seconds = float(seconds_value)
        except (TypeError, ValueError):
            continue
        power = _number(watts[index]) if index < len(watts) else None
        heart_rate = _number(heart_rates[index]) if index < len(heart_rates) else None
        power_rows.append((started_at + timedelta(seconds=seconds), power))
        if power is not None and heart_rate is not None and heart_rate > 0:
            paired_rows.append({"secs": seconds, "power": power, "hr": heart_rate})
    return power_rows, paired_rows


def _matching_workout_id(db: Session, user_id: UUID, local_date: date) -> UUID | None:
    available = [
        workout.id
        for workout, activity_id in list_workouts_for_user_on_date(db, user_id, local_date)
        if activity_id is None
    ]
    return available[0] if len(available) == 1 else None


def _build_activity_record(
    db: Session,
    user_id: UUID,
    detail: dict,
    streams: dict[str, list],
    *,
    timezone_name: str,
    ftp: float,
) -> ActivityRecord:
    external_id = str(detail["id"])
    started_at_aware = datetime.fromisoformat(str(detail["start_date"]).replace("Z", "+00:00"))
    started_at = started_at_aware.astimezone(timezone.utc).replace(tzinfo=None)
    duration_seconds = float(detail.get("moving_time") or detail.get("elapsed_time") or 0)
    if duration_seconds <= 0:
        raise ValueError("La actividad no contiene una duración válida.")

    has_measured_power = detail.get("device_watts") is True
    power_rows, paired_rows = _stream_rows(detail, streams)
    measured_power = [power for _, power in power_rows if power is not None]
    heart_values = [
        _number(value)
        for value in streams.get("heartrate", [])
        if _number(value) is not None and _number(value) > 0  # type: ignore[operator]
    ]
    normalized_power = _normalized_power(power_rows) if has_measured_power else None
    decoupling, _ = _decoupling(paired_rows)
    metrics = _complete_power_metrics(
        {
            "duration_minutes": round(duration_seconds / 60, 2),
            "normalized_power": round(normalized_power, 2) if normalized_power is not None else None,
            "intensity_factor": None,
            "tss": None,
        },
        ftp,
        {},
    )
    local_date = started_at_aware.astimezone(ZoneInfo(timezone_name)).date()
    return ActivityRecord(
        user_id=user_id,
        planned_workout_id=_matching_workout_id(db, user_id, local_date),
        title=str(detail.get("name") or "Actividad de ciclismo")[:255],
        started_at=started_at,
        sport="CYCLING",
        duration_minutes=round(duration_seconds / 60, 2),
        distance_km=_number(detail.get("distance"), 1000),
        average_power=round(mean(measured_power), 2) if measured_power else None,
        normalized_power=metrics.get("normalized_power"),
        average_heart_rate=round(mean(heart_values), 2) if heart_values else _number(detail.get("average_heartrate")),
        intensity_factor=metrics.get("intensity_factor"),
        tss=metrics.get("tss"),
        perceived_exertion=None,
        aerobic_decoupling=decoupling,
        source="EXTERNAL",
        external_source_id=external_id,
        notes="Importada automáticamente desde Strava.",
    )


SYNCED_ACTIVITY_FIELDS = (
    "title",
    "started_at",
    "duration_minutes",
    "distance_km",
    "average_power",
    "normalized_power",
    "average_heart_rate",
    "intensity_factor",
    "tss",
    "aerobic_decoupling",
)


def _same_local_date(first: datetime, second: datetime, timezone_name: str) -> bool:
    zone = ZoneInfo(timezone_name)
    return first.replace(tzinfo=timezone.utc).astimezone(zone).date() == second.replace(
        tzinfo=timezone.utc
    ).astimezone(zone).date()


def _update_existing_activity(
    existing: ActivityRecord,
    fresh: ActivityRecord,
    *,
    timezone_name: str,
) -> bool:
    changed = existing.external_status != "ACTIVE"
    same_date = _same_local_date(existing.started_at, fresh.started_at, timezone_name)
    for field in SYNCED_ACTIVITY_FIELDS:
        value = getattr(fresh, field)
        if getattr(existing, field) != value:
            setattr(existing, field, value)
            changed = True
    if not same_date and existing.planned_workout_id != fresh.planned_workout_id:
        existing.planned_workout_id = fresh.planned_workout_id
        changed = True
    existing.external_status = "ACTIVE"
    return changed


def _save_sync_result(
    connection: ExternalConnection,
    *,
    new: int,
    updated: int,
    deleted: int,
    unchanged: int,
    failed: int,
    last_error: str | None,
) -> None:
    connection.last_sync_new = new
    connection.last_sync_updated = updated
    connection.last_sync_deleted = deleted
    connection.last_sync_unchanged = unchanged
    connection.last_sync_failed = failed
    connection.sync_failed = failed
    connection.sync_last_error = last_error


def _reconcile_strava_activities(
    db: Session,
    user_id: UUID,
    connection: ExternalConnection,
    client: StravaClient,
    cipher: TokenCipher,
    *,
    timezone_name: str,
    ftp: float,
    full: bool,
    start_date: date | None = None,
) -> StravaSyncResult:
    if start_date is not None:
        connection.sync_start_date = start_date
        connection.sync_enabled = True
    if connection.sync_start_date is None or (not full and not connection.sync_enabled):
        today = datetime.now(ZoneInfo(timezone_name)).date()
        return StravaSyncResult(status="NOT_CONFIGURED", total=0, imported=0, skipped=0, failed=0, start_date=today)

    zone = ZoneInfo(timezone_name)
    configured_start = datetime.combine(connection.sync_start_date, time.min, zone)
    if full or connection.sync_cursor_at is None:
        range_start = configured_start
    else:
        cursor = connection.sync_cursor_at.replace(tzinfo=timezone.utc).astimezone(zone)
        range_start = max(configured_start, cursor - timedelta(days=7))

    started_at = datetime.now(timezone.utc).replace(tzinfo=None)
    connection.sync_status = "RUNNING"
    connection.last_sync_attempt_at = started_at
    connection.sync_last_error = None
    db.commit()

    after = int(range_start.timestamp())
    before = int((datetime.now(timezone.utc) + timedelta(days=1)).timestamp())
    raw_items: list[dict] = []
    new = updated = deleted = unchanged = failed = 0
    last_error: str | None = None
    latest_started_at = connection.sync_cursor_at
    try:
        access_token = valid_access_token(db, connection, client, cipher)
        page = 1
        while True:
            batch = client.list_athlete_activities(
                access_token,
                after=after,
                before=before,
                page=page,
                per_page=100,
            )
            raw_items.extend(item for item in batch if str(item.get("sport_type") or item.get("type") or "") in CYCLING_TYPES)
            if len(batch) < 100:
                break
            page += 1
            if page > 100:
                raise ValueError("El intervalo contiene demasiadas actividades para una sola sincronización.")

        visible_ids = {str(item.get("id")) for item in raw_items if item.get("id") is not None}
        existing_by_id = {
            activity.external_source_id: activity
            for activity in db.scalars(
                select(ActivityRecord).where(
                    ActivityRecord.user_id == user_id,
                    ActivityRecord.source == "EXTERNAL",
                    ActivityRecord.external_source_id.in_(visible_ids),
                )
            )
        } if visible_ids else {}

        range_start_utc = range_start.astimezone(timezone.utc).replace(tzinfo=None)
        range_end_utc = datetime.fromtimestamp(before, timezone.utc).replace(tzinfo=None)
        stored_in_range = list(
            db.scalars(
                select(ActivityRecord).where(
                    ActivityRecord.user_id == user_id,
                    ActivityRecord.source == "EXTERNAL",
                    ActivityRecord.started_at >= range_start_utc,
                    ActivityRecord.started_at < range_end_utc,
                )
            )
        )
        for stored in stored_in_range:
            if stored.external_source_id not in visible_ids and stored.external_status != "DELETED_AT_SOURCE":
                stored.external_status = "DELETED_AT_SOURCE"
                stored.planned_workout_id = None
                deleted += 1

        for summary in raw_items:
            external_id = str(summary.get("id") or "")
            if not external_id:
                continue
            try:
                detail = client.get_activity(access_token, external_id)
                streams = client.get_activity_streams(access_token, external_id)
                fresh = _build_activity_record(
                    db,
                    user_id,
                    detail,
                    streams,
                    timezone_name=timezone_name,
                    ftp=ftp,
                )
                existing = existing_by_id.get(external_id)
                if existing is None:
                    db.add(fresh)
                    db.flush()
                    existing_by_id[external_id] = fresh
                    new += 1
                    current = fresh
                else:
                    current = existing
                    if _update_existing_activity(existing, fresh, timezone_name=timezone_name):
                        updated += 1
                    else:
                        unchanged += 1
                if latest_started_at is None or current.started_at > latest_started_at:
                    latest_started_at = current.started_at
            except (StravaAuthenticationError, StravaRateLimitError, StravaUnavailableError):
                raise
            except (StravaError, KeyError, TypeError, ValueError):
                failed += 1
                last_error = f"No se pudo actualizar la actividad {external_id}."

        finished_at = datetime.now(timezone.utc).replace(tzinfo=None)
        connection.sync_cursor_at = latest_started_at
        connection.last_sync_at = finished_at
        connection.sync_status = "COMPLETED_WITH_ERRORS" if failed else "COMPLETED"
        connection.sync_total += new
        connection.sync_imported += new
        connection.sync_skipped = unchanged
        _save_sync_result(
            connection,
            new=new,
            updated=updated,
            deleted=deleted,
            unchanged=unchanged,
            failed=failed,
            last_error=last_error,
        )
        db.commit()
    except Exception as exc:
        db.rollback()
        connection.sync_status = "FAILED"
        connection.sync_last_error = str(exc)[:1000]
        connection.last_sync_failed = max(failed, 1)
        if isinstance(exc, StravaAuthenticationError):
            connection.status = "REAUTHORIZATION_REQUIRED"
        db.commit()
        raise

    return StravaSyncResult(
        status=connection.sync_status,
        total=len(raw_items),
        imported=new,
        skipped=unchanged,
        failed=failed,
        start_date=range_start.date(),
        last_error=last_error,
        new=new,
        updated=updated,
        deleted=deleted,
        unchanged=unchanged,
        started_at=started_at,
        finished_at=finished_at,
    )


def sync_strava_activities(
    db: Session,
    user_id: UUID,
    connection: ExternalConnection,
    client: StravaClient,
    cipher: TokenCipher,
    *,
    start_date: date,
    timezone_name: str,
    ftp: float,
) -> StravaSyncResult:
    return _reconcile_strava_activities(
        db, user_id, connection, client, cipher,
        timezone_name=timezone_name, ftp=ftp, full=True, start_date=start_date,
    )


def sync_incremental_strava_activities(
    db: Session, user_id: UUID, connection: ExternalConnection, client: StravaClient,
    cipher: TokenCipher, *, timezone_name: str, ftp: float,
) -> StravaSyncResult:
    return _reconcile_strava_activities(
        db, user_id, connection, client, cipher,
        timezone_name=timezone_name, ftp=ftp, full=False,
    )


def sync_full_strava_activities(
    db: Session, user_id: UUID, connection: ExternalConnection, client: StravaClient,
    cipher: TokenCipher, *, timezone_name: str, ftp: float,
) -> StravaSyncResult:
    return _reconcile_strava_activities(
        db, user_id, connection, client, cipher,
        timezone_name=timezone_name, ftp=ftp, full=True,
    )
