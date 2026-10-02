from app.models.aerobic_response import AerobicResponse
from app.models.load_decision import LoadDecision
from app.models.training_plan import TrainingPlan
from app.models.workout import (
    IntervalBlock,
    SessionPhase,
    Workout,
    WorkoutType,
)

from app.services.training_plan_summary_service import (
    build_training_plan_summary,
)

def test_build_training_plan_summary():
    plan = TrainingPlan(
        requested_target_tss=300,
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
        "requested_target_tss": 300,
        "target_tss": 263.5,
        "feasibility_adjusted": True,
        "estimated_total_tss": 98.5,
        "estimated_tss_difference": -165.0,
        "total_duration_minutes": 90,
        "expected_aerobic_decoupling": 7.0,
        "response_prediction_method": "unavailable",
        "response_evaluated_target_tss": None,
        "workout_response_predictions": [],
        "aerobic_response": "ELEVATED",
        "load_decision": "REDUCE",
        "workouts": [
            {
                "day": "TUESDAY",
                "workout_type": "ENDURANCE",
                "target_tss": 100,
                "estimated_tss": 98.5,
                "duration_minutes": 90,
                "target_power_min": 150,
                "target_power_max": 190,
                "warmup": None,
                "intervals": None,
                "cooldown": None,
            },
        ],
    }

def test_build_training_plan_summary_with_intervals():
    plan = TrainingPlan(
        target_tss=100,
        workouts=[
            Workout(
                day="FRIDAY",
                workout_type=WorkoutType.THRESHOLD,
                target_tss=100,
                estimated_tss=98,
                duration_minutes=75,
                warmup=SessionPhase(
                    duration_minutes=15,
                    target_power_min=125,
                    target_power_max=175,
                ),
                intervals=IntervalBlock(
                    repetitions=4,
                    work_minutes=8,
                    recovery_minutes=4,
                    work_power_min=238,
                    work_power_max=263,
                    recovery_power_min=125,
                    recovery_power_max=150,
                ),
                cooldown=SessionPhase(
                    duration_minutes=12,
                    target_power_min=100,
                    target_power_max=150,
                ),
            ),
        ],
    )

    result = build_training_plan_summary(plan)

    workout = result["workouts"][0]

    assert workout["warmup"] == {
        "duration_minutes": 15,
        "target_power_min": 125,
        "target_power_max": 175,
    }

    assert workout["intervals"] == {
        "repetitions": 4,
        "work_minutes": 8,
        "recovery_minutes": 4,
        "work_power_min": 238,
        "work_power_max": 263,
        "recovery_power_min": 125,
        "recovery_power_max": 150,
    }

    assert workout["cooldown"] == {
        "duration_minutes": 12,
        "target_power_min": 100,
        "target_power_max": 150,
    }

def test_build_cold_start_training_plan_summary():
    plan = TrainingPlan(
        target_tss=288,
        workouts=[],
    )

    result = build_training_plan_summary(plan)

    assert result["expected_aerobic_decoupling"] is None
    assert result["response_prediction_method"] == "unavailable"
    assert result["response_evaluated_target_tss"] is None
    assert result["workout_response_predictions"] == []
    assert result["aerobic_response"] == "UNKNOWN"
    assert result["load_decision"] is None
