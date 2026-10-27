from datetime import date, datetime, timezone
from enum import Enum
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_serializer, field_validator


class Sport(str, Enum):
    CYCLING = "CYCLING"


class ActivitySource(str, Enum):
    MANUAL = "MANUAL"
    GOLDENCHEETAH = "GOLDENCHEETAH"
    FILE_IMPORT = "FILE_IMPORT"
    EXTERNAL = "EXTERNAL"


class ActivityInput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    title: str = Field(min_length=1, max_length=255)
    started_at: datetime
    sport: Sport = Sport.CYCLING
    duration_minutes: float = Field(gt=0)
    distance_km: float | None = Field(default=None, ge=0)
    average_power: float | None = Field(default=None, ge=0)
    normalized_power: float | None = Field(default=None, ge=0)
    average_heart_rate: float | None = Field(default=None, gt=0)
    intensity_factor: float | None = Field(default=None, ge=0)
    tss: float | None = Field(default=None, ge=0)
    perceived_exertion: int | None = Field(default=None, ge=1, le=10)
    aerobic_decoupling: float | None = None
    notes: str | None = Field(default=None, max_length=4000)

    @field_validator("title")
    @classmethod
    def title_not_blank(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("title no puede estar vacío")
        return value

    @field_validator("started_at")
    @classmethod
    def require_timezone(cls, value: datetime) -> datetime:
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError("started_at debe incluir zona horaria")
        return value.astimezone(timezone.utc).replace(tzinfo=None)

    @field_serializer("started_at", when_used="json")
    def serialize_started_at(self, value: datetime) -> str:
        """Expose the internally stored naive UTC value as an absolute instant."""
        if value.tzinfo is None:
            value = value.replace(tzinfo=timezone.utc)
        return value.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")


class ActivityCreate(ActivityInput):
    pass


class ActivityUpdate(ActivityInput):
    pass


class ActivityRead(ActivityInput):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    planned_workout_id: UUID | None
    started_at: datetime
    source: ActivitySource
    estimated_load: float | None
    load_source: str
    created_at: datetime
    updated_at: datetime

    @field_validator("started_at", mode="before")
    @classmethod
    def output_utc(cls, value: datetime) -> datetime:
        if value.tzinfo is None:
            return value.replace(tzinfo=timezone.utc)
        return value.astimezone(timezone.utc)


class ActivityListResponse(BaseModel):
    items: list[ActivityRead]
    total: int
    limit: int
    offset: int


class ActivityWorkoutLink(BaseModel):
    model_config = ConfigDict(extra="forbid")

    planned_workout_id: UUID | None


class AvailableWorkoutRead(BaseModel):
    id: UUID
    scheduled_date: date
    workout_type: str
    duration_minutes: int | None
    estimated_tss: float | None
    target_tss: float
    already_linked: bool
    linked_activity_id: UUID | None


class ActivityImportPreview(BaseModel):
    filename: str
    fingerprint: str
    duplicate: bool
    activity: ActivityCreate


class ActivityImportCommit(ActivityCreate):
    filename: str = Field(min_length=1, max_length=255)
    fingerprint: str = Field(pattern=r"^[0-9a-f]{64}$")
    planned_workout_id: UUID | None = None
