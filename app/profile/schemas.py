from datetime import date, datetime
from enum import Enum
from uuid import UUID
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from app.models.cyclist import Level, Modality
from app.models.training_objective import Objective


class Weekday(str, Enum):
    MONDAY = "MONDAY"
    TUESDAY = "TUESDAY"
    WEDNESDAY = "WEDNESDAY"
    THURSDAY = "THURSDAY"
    FRIDAY = "FRIDAY"
    SATURDAY = "SATURDAY"
    SUNDAY = "SUNDAY"


DAY_ORDER = {day.value: index for index, day in enumerate(Weekday)}


class CyclistProfileUpsert(BaseModel):
    ftp: float = Field(gt=0, le=600)
    weekly_hours: float = Field(gt=0, le=40)
    available_days: list[Weekday] = Field(min_length=1)
    modality: Modality
    level: Level
    objective: Objective
    target_date: date | None = None
    timezone: str = "Europe/Madrid"

    @field_validator("available_days")
    @classmethod
    def validate_available_days(cls, value: list[Weekday]) -> list[Weekday]:
        if len(set(value)) != len(value):
            raise ValueError("available_days no puede contener días duplicados")
        return sorted(value, key=lambda day: DAY_ORDER[day.value])

    @field_validator("timezone")
    @classmethod
    def validate_timezone(cls, value: str) -> str:
        try:
            ZoneInfo(value)
        except ZoneInfoNotFoundError as exc:
            raise ValueError("timezone debe ser una zona IANA válida") from exc
        return value

    @model_validator(mode="after")
    def validate_target_date(self) -> "CyclistProfileUpsert":
        if self.objective is Objective.RACE and self.target_date is None:
            raise ValueError("target_date es obligatorio para el objetivo RACE")
        return self


class CyclistProfileRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    user_id: UUID
    ftp: float
    weekly_hours: float
    available_days: list[Weekday]
    modality: Modality
    level: Level
    objective: Objective
    target_date: date | None
    timezone: str
    onboarding_completed_at: datetime
    created_at: datetime
    updated_at: datetime
