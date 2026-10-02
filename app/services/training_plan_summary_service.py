from app.models.training_plan import TrainingPlan

def build_training_plan_summary(
    plan: TrainingPlan,
) -> dict:
    """Convierte un plan de entrenamiento en una estructura presentable."""
    return {
        "target_tss": plan.target_tss,
        "expected_aerobic_decoupling": (
            plan.expected_aerobic_decoupling
        ),
        "aerobic_response": plan.aerobic_response.value,
        "load_decision": (
            plan.load_decision.value
            if plan.load_decision is not None
            else None
        ),
        "workouts": [
            {
                "day": workout.day,
                "workout_type": workout.workout_type.value,
                "duration_minutes": workout.duration_minutes,
                "estimated_tss": workout.estimated_tss,
                "target_power_min": workout.target_power_min,
                "target_power_max": workout.target_power_max,
            }
            for workout in plan.workouts
        ],
    }
