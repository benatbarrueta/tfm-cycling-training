from app.models.training_plan import TrainingPlan
from app.models.workout import IntervalBlock, SessionPhase


def build_session_phase_summary(
    phase: SessionPhase | None,
) -> dict | None:
    """Convierte una fase de sesión en un diccionario."""
    if phase is None:
        return None

    return {
        "duration_minutes": phase.duration_minutes,
        "target_power_min": phase.target_power_min,
        "target_power_max": phase.target_power_max,
    }

def build_interval_summary(
    intervals: IntervalBlock | None,
) -> dict | None:
    """Convierte un bloque de intervalos en un diccionario."""
    if intervals is None:
        return None

    return {
        "repetitions": intervals.repetitions,
        "work_minutes": intervals.work_minutes,
        "recovery_minutes": intervals.recovery_minutes,
        "work_power_min": intervals.work_power_min,
        "work_power_max": intervals.work_power_max,
        "recovery_power_min": intervals.recovery_power_min,
        "recovery_power_max": intervals.recovery_power_max,
    }

def build_training_plan_summary(
    plan: TrainingPlan,
) -> dict:
    """Convierte un plan de entrenamiento en una estructura presentable."""
    estimated_total_tss = round(
        sum(
            workout.estimated_tss
            for workout in plan.workouts
            if workout.estimated_tss is not None
        ),
        2,
    )

    total_duration_minutes = sum(
        workout.duration_minutes
        for workout in plan.workouts
        if workout.duration_minutes is not None
    )

    return {
        "requested_target_tss": plan.requested_target_tss,
        "target_tss": plan.target_tss,
        "feasibility_adjusted": (
            plan.requested_target_tss is not None
            and plan.target_tss != plan.requested_target_tss
        ),
        "estimated_total_tss": estimated_total_tss,
        "estimated_tss_difference": round(
            estimated_total_tss - plan.target_tss,
            2,
        ),
        "total_duration_minutes": total_duration_minutes,
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
                "target_tss": workout.target_tss,
                "estimated_tss": workout.estimated_tss,
                "duration_minutes": workout.duration_minutes,
                "target_power_min": workout.target_power_min,
                "target_power_max": workout.target_power_max,
                "warmup": build_session_phase_summary(
                    workout.warmup
                ),
                "intervals": build_interval_summary(
                    workout.intervals
                ),
                "cooldown": build_session_phase_summary(
                    workout.cooldown
                ),
            }
            for workout in plan.workouts
        ],
    }
