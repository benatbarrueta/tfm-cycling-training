from app.models.training_objective import Objective, RacePhase
from app.models.workout import WorkoutType


OBJECTIVE_PRIORITIES = {
    Objective.ENDURANCE: {
        WorkoutType.RECOVERY: 2,
        WorkoutType.ENDURANCE: 5,
        WorkoutType.TEMPO: 4,
        WorkoutType.THRESHOLD: 2,
        WorkoutType.VO2MAX: 1,
    },

    Objective.PERFORMANCE: {
        WorkoutType.RECOVERY: 2,
        WorkoutType.ENDURANCE: 4,
        WorkoutType.TEMPO: 3,
        WorkoutType.THRESHOLD: 4,
        WorkoutType.VO2MAX: 3,
    },
}

RACE_PHASE_PRIORITIES = {
    RacePhase.BASE: {
        WorkoutType.RECOVERY: 2,
        WorkoutType.ENDURANCE: 5,
        WorkoutType.TEMPO: 4,
        WorkoutType.THRESHOLD: 2,
        WorkoutType.VO2MAX: 1,
    },

    RacePhase.BUILD: {
        WorkoutType.RECOVERY: 2,
        WorkoutType.ENDURANCE: 4,
        WorkoutType.TEMPO: 3,
        WorkoutType.THRESHOLD: 5,
        WorkoutType.VO2MAX: 4,
    },

    RacePhase.PEAK: {
        WorkoutType.RECOVERY: 2,
        WorkoutType.ENDURANCE: 3,
        WorkoutType.TEMPO: 3,
        WorkoutType.THRESHOLD: 4,
        WorkoutType.VO2MAX: 4,
    },

    RacePhase.TAPER: {
        WorkoutType.RECOVERY: 4,
        WorkoutType.ENDURANCE: 3,
        WorkoutType.TEMPO: 2,
        WorkoutType.THRESHOLD: 2,
        WorkoutType.VO2MAX: 2,
    },
}

RACE_PHASE_DAY_LIMITS = {
    RacePhase.TAPER: 14,
    RacePhase.PEAK: 56,
    RacePhase.BUILD: 112,
}