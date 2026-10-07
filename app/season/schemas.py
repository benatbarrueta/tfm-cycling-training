from datetime import date, datetime
from enum import Enum
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class PlanStatus(str, Enum):
    ACTIVE = "ACTIVE"
    COMPLETED = "COMPLETED"
    CANCELLED = "CANCELLED"


class PhaseType(str, Enum):
    BASE = "BASE"
    BUILD = "BUILD"
    PEAK = "PEAK"
    TAPER = "TAPER"


class WeekStatus(str, Enum):
    PROVISIONAL = "PROVISIONAL"
    ACTIVE = "ACTIVE"
    COMPLETED = "COMPLETED"
    CANCELLED = "CANCELLED"


class SeasonPlanCreate(BaseModel):
    name: str


class PlannedWorkoutRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    position: int
    scheduled_date: date
    day: str
    workout_type: str
    target_tss: float
    estimated_tss: float | None
    duration_minutes: int | None
    target_power_min: float | None
    target_power_max: float | None
    warmup: dict | None
    intervals: dict | None
    cooldown: dict | None
    predicted_aerobic_decoupling: float | None
    aerobic_response: str | None
    outside_training_range_features: list[str] | None


class PlannedWeekRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    position: int
    week_start: date
    week_end: date
    status: str
    focus: str
    phase: str
    provisional_target_tss: float
    provisional_hours: float
    requested_target_tss: float | None
    adapted_target_tss: float | None
    estimated_total_tss: float | None
    expected_aerobic_decoupling: float | None
    response_prediction_method: str | None
    load_decision: str | None
    generated_at: datetime | None
    workouts: list[PlannedWorkoutRead] = Field(default_factory=list)


class TrainingPhaseRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    phase_type: str
    position: int
    start_date: date
    end_date: date
    week_count: int


class SeasonPlanRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    name: str
    status: str
    start_date: date
    target_date: date
    objective: str
    modality: str
    level: str
    ftp_snapshot: float
    weekly_hours_snapshot: float
    available_days_snapshot: list[str]
    generator_version: str
    created_at: datetime
    updated_at: datetime
    phases: list[TrainingPhaseRead] = Field(default_factory=list)
    weeks: list[PlannedWeekRead] = Field(default_factory=list)
