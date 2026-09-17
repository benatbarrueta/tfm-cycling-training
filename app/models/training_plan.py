from dataclasses import dataclass

from app.models.workout import Workout


@dataclass
class TrainingPlan:
    target_tss: float
    workouts: list[Workout]