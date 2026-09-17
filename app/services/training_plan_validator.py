from app.config.training_rules import LEVEL_RULES
from app.models.cyclist import Cyclist
from app.models.training_plan import TrainingPlan
from app.models.workout import WorkoutType


def validate_plan_for_level(
    plan: TrainingPlan,
    cyclist: Cyclist,
) -> None:
    rules = LEVEL_RULES[cyclist.level]

    intense_workouts = [
        workout
        for workout in plan.workouts
        if workout.workout_type in {
            WorkoutType.THRESHOLD,
            WorkoutType.VO2MAX,
        }
    ]

    if len(intense_workouts) > rules["max_intense_workouts_per_week"]:
        raise ValueError(
            "Training plan exceeds intensity limits for cyclist level"
        )