from app.models.workout import WorkoutType
from app.models.cyclist import Level

INTERVAL_RULES = {
    WorkoutType.THRESHOLD: {
        "min_work_minutes": 10,
        "max_work_minutes": 30,
        "work_step_minutes": 5,

        "min_repetitions": 2,
        "max_repetitions": 3,

        "min_total_work_minutes": 20,
        "max_total_work_minutes": 60,

        "recovery_minutes": 5,

        "warmup_minutes": 15,
        "cooldown_minutes": 10,

        "warmup_if": 0.60,
        "recovery_if": 0.50,
        "cooldown_if": 0.50,
    },

    WorkoutType.VO2MAX: {
        "min_work_minutes": 3,
        "max_work_minutes": 8,
        "work_step_minutes": 1,

        "min_repetitions": 3,
        "max_repetitions": 6,

        "min_total_work_minutes": 12,
        "max_total_work_minutes": 30,

        "recovery_minutes": 4,

        "warmup_minutes": 15,
        "cooldown_minutes": 10,

        "warmup_if": 0.60,
        "recovery_if": 0.50,
        "cooldown_if": 0.50,
    },
}

CONTINUOUS_WORKOUT_RULES = {
    WorkoutType.RECOVERY: {
        "estimated_if": 0.50,
    },
    WorkoutType.ENDURANCE: {
        "estimated_if": 0.65,
    },
    WorkoutType.TEMPO: {
        "estimated_if": 0.83,
    },
}

LEVEL_RULES = {
    Level.BEGINNER: {
        "max_intense_workouts_per_week": 1,
        "max_vo2max_total_minutes": 20,
        "max_threshold_total_minutes": 30,
    },

    Level.INTERMEDIATE: {
        "max_intense_workouts_per_week": 2,
        "max_vo2max_total_minutes": 30,
        "max_threshold_total_minutes": 45,
    },

    Level.ADVANCED: {
        "max_intense_workouts_per_week": 3,
        "max_vo2max_total_minutes": 40,
        "max_threshold_total_minutes": 60,
    },
}