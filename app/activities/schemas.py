from datetime import datetime, timezone
from enum import Enum
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator


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
