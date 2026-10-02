from app.models.aerobic_response import AerobicResponse
from app.models.load_decision import LoadDecision
from app.models.training_plan import TrainingPlan
from app.models.workout import Workout, WorkoutType
from app.services.training_plan_summary_service import (
    build_training_plan_summary,
)

def test_build_training_plan_summary():
    plan = TrainingPlan(
        target_tss=263.5,
        expected_aerobic_decoupling=7.0,
        aerobic_response=AerobicResponse.ELEVATED,
        load_decision=LoadDecision.REDUCE,
        workouts=[
            Workout(
                day="TUESDAY",
                workout_type=WorkoutType.ENDURANCE,
                target_tss=100,
                estimated_tss=98.5,
                duration_minutes=90,
                target_power_min=150,
                target_power_max=190,
            ),
        ],
    )

    result = build_training_plan_summary(plan)

    assert result == {
        "target_tss": 263.5,
        "expected_aerobic_decoupling": 7.0,
        "aerobic_response": "ELEVATED",
        "load_decision": "REDUCE",
        "workouts": [
            {
                "day": "TUESDAY",
                "workout_type": "ENDURANCE",
                "duration_minutes": 90,
                "estimated_tss": 98.5,
                "target_power_min": 150,
                "target_power_max": 190,
            },
        ],
    }

def test_build_cold_start_training_plan_summary():
    plan = TrainingPlan(
        target_tss=288,
        workouts=[],
    )

    result = build_training_plan_summary(plan)

    assert result["expected_aerobic_decoupling"] is None
    assert result["aerobic_response"] == "UNKNOWN"
    assert result["load_decision"] is None
