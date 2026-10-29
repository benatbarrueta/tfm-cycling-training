from datetime import date, datetime

from pydantic import BaseModel


class ExternalConnectionRead(BaseModel):
    provider: str
    configured: bool
    connected: bool
    status: str | None = None
    external_display_name: str | None = None
    connected_at: datetime | None = None
    last_sync_at: datetime | None = None
    sync_start_date: date | None = None
    sync_enabled: bool = False
    sync_status: str = "NOT_CONFIGURED"
    sync_total: int = 0
    sync_imported: int = 0
    sync_skipped: int = 0
    sync_failed: int = 0
    sync_last_error: str | None = None


class IntegrationList(BaseModel):
    items: list[ExternalConnectionRead]


class ConnectResponse(BaseModel):
    authorization_url: str


class StravaActivityCandidate(BaseModel):
    external_id: str
    name: str
    sport_type: str
    started_at: datetime
    duration_minutes: float
    distance_km: float | None = None
    elevation_gain_m: float | None = None
    average_power: float | None = None
    normalized_power: float | None = None
    average_heart_rate: float | None = None
    trainer: bool = False
    commute: bool = False
    already_imported: bool = False


class StravaActivityList(BaseModel):
    items: list[StravaActivityCandidate]
    page: int
    limit: int
    has_more: bool


class StravaSyncRequest(BaseModel):
    start_date: date


class StravaSyncResult(BaseModel):
    status: str
    total: int
    imported: int
    skipped: int
    failed: int
    start_date: date
    last_error: str | None = None
