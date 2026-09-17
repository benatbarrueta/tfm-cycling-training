from dataclasses import dataclass
from enum import Enum


class WorkoutType(Enum):
    RECOVERY = "RECOVERY"
    ENDURANCE = "ENDURANCE"
    TEMPO = "TEMPO"
    THRESHOLD = "THRESHOLD"
    VO2MAX = "VO2MAX"


@dataclass
class SessionPhase:
    duration_minutes: float
    target_power_min: float | None = None
    target_power_max: float | None = None


@dataclass
class IntervalBlock:
    repetitions: int

    work_minutes: float
    recovery_minutes: float

    work_power_min: float
    work_power_max: float

    recovery_power_min: float
    recovery_power_max: float


@dataclass
class Workout:
    day: str
    workout_type: WorkoutType
    target_tss: float

    estimated_tss: float | None = None
    duration_minutes: int | None = None

    target_power_min: float | None = None
    target_power_max: float | None = None

    warmup: SessionPhase | None = None
    intervals: IntervalBlock | None = None
    cooldown: SessionPhase | None = None