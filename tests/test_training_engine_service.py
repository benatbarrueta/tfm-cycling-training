import pytest
from datetime import date

from app.models.activity import Activity
from app.models.cyclist import Cyclist, Level, Modality
from app.models.training_objective import Objective
from app.models.aerobic_response import AerobicResponse
from app.models.load_decision import LoadDecision

from app.services.training_engine_service import (
    generate_personalized_training_plan,
)

def test_generate_personalized_training_plan():
    cyclist = Cyclist(
        cyclist_id=1,
        modalities=[Modality.XCO],
        level=Level.INTERMEDIATE,
        ftp=250,
        weekly_hours=8,
        available_days=[
            "TUESDAY",
            "WEDNESDAY",
            "FRIDAY",
            "SUNDAY",
        ],
        objective=Objective.PERFORMANCE,
    )

    activities = [
        # Semana anterior
        Activity(
            date=date(2026, 9, 7),
            duration_minutes=60,
            average_power=180,
            normalized_power=200,
        ),
        Activity(
            date=date(2026, 9, 10),
            duration_minutes=60,
            average_power=190,
            normalized_power=225,
        ),

        # Semana actual
        Activity(
            date=date(2026, 9, 14),
            duration_minutes=60,
            average_power=185,
            normalized_power=200,
        ),
        Activity(
            date=date(2026, 9, 15),
            duration_minutes=60,
            average_power=190,
            normalized_power=225,
        ),
        Activity(
            date=date(2026, 9, 16),
            duration_minutes=60,
            average_power=200,
            normalized_power=225,
        ),
    ]

    plan = generate_personalized_training_plan(
        cyclist=cyclist,
        modality=Modality.XCO,
        activities=activities,
        reference_date=date(2026, 9, 16),
    )

    assert plan is not None
    assert plan.target_tss > 0
    assert len(plan.workouts) == 4

    for workout in plan.workouts:
        assert workout.duration_minutes is not None
        assert workout.estimated_tss is not None

def test_generate_personalized_training_plan_with_no_history():
    cyclist = Cyclist(
        cyclist_id=1,
        modalities=[Modality.XCO],
        level=Level.INTERMEDIATE,
        ftp=250,
        weekly_hours=8,
        available_days=[
            "TUESDAY",
            "WEDNESDAY",
            "FRIDAY",
            "SUNDAY",
        ],
        objective=Objective.PERFORMANCE,
    )

    plan = generate_personalized_training_plan(
        cyclist=cyclist,
        modality=Modality.XCO,
        activities=[],
        reference_date=date(2026, 9, 16),
    )

    assert plan is not None
    assert plan.target_tss > 0
    assert len(plan.workouts) == 4

    for workout in plan.workouts:
        assert workout.duration_minutes is not None
        assert workout.estimated_tss is not None

def test_generate_personalized_training_plan_with_insufficient_history():
    cyclist = Cyclist(
        cyclist_id=1,
        modalities=[Modality.XCO],
        level=Level.INTERMEDIATE,
        ftp=250,
        weekly_hours=8,
        available_days=[
            "TUESDAY",
            "WEDNESDAY",
            "FRIDAY",
            "SUNDAY",
        ],
        objective=Objective.PERFORMANCE,
    )

    activities = [
        Activity(
            date=date(2026, 9, 15),
            duration_minutes=60,
            average_power=190,
            normalized_power=210,
        ),
    ]

    plan = generate_personalized_training_plan(
        cyclist=cyclist,
        modality=Modality.XCO,
        activities=activities,
        reference_date=date(2026, 9, 16),
    )

    assert plan is not None
    assert plan.target_tss > 0
    assert len(plan.workouts) == 4

def test_elevated_aerobic_response_reduces_target_tss():
    cyclist = Cyclist(
        cyclist_id=1,
        modalities=[Modality.XCO],
        level=Level.INTERMEDIATE,
        ftp=250,
        weekly_hours=8,
        available_days=[
            "TUESDAY",
            "WEDNESDAY",
            "FRIDAY",
            "SUNDAY",
        ],
        objective=Objective.PERFORMANCE,
    )

    activities = [
        Activity(
            date=date(2026, 9, 1),
            duration_minutes=60,
            average_power=180,
            normalized_power=200,
            tss=150,
            aerobic_decoupling=7.0,
        ),
        Activity(
            date=date(2026, 9, 3),
            duration_minutes=60,
            average_power=180,
            normalized_power=200,
            tss=150,
            aerobic_decoupling=8.0,
        ),
        Activity(
            date=date(2026, 9, 7),
            duration_minutes=60,
            average_power=180,
            normalized_power=200,
            tss=155,
            aerobic_decoupling=6.0,
        ),
        Activity(
            date=date(2026, 9, 10),
            duration_minutes=60,
            average_power=180,
            normalized_power=200,
            tss=155,
        ),
    ]

    plan = generate_personalized_training_plan(
        cyclist=cyclist,
        modality=Modality.XCO,
        activities=activities,
        reference_date=date(2026, 9, 16),
    )

    assert plan.target_tss == 263.5

def test_plan_reports_aerobic_response_and_load_decision():
    cyclist = Cyclist(
        cyclist_id=1,
        modalities=[Modality.XCO],
        level=Level.INTERMEDIATE,
        ftp=250,
        weekly_hours=8,
        available_days=[
            "TUESDAY",
            "WEDNESDAY",
            "FRIDAY",
            "SUNDAY",
        ],
        objective=Objective.PERFORMANCE,
    )

    activities = [
        Activity(
            date=date(2026, 9, 1),
            duration_minutes=60,
            average_power=180,
            normalized_power=200,
            tss=150,
            aerobic_decoupling=7.0,
        ),
        Activity(
            date=date(2026, 9, 3),
            duration_minutes=60,
            average_power=180,
            normalized_power=200,
            tss=150,
            aerobic_decoupling=8.0,
        ),
        Activity(
            date=date(2026, 9, 7),
            duration_minutes=60,
            average_power=180,
            normalized_power=200,
            tss=155,
            aerobic_decoupling=6.0,
        ),
        Activity(
            date=date(2026, 9, 10),
            duration_minutes=60,
            average_power=180,
            normalized_power=200,
            tss=155,
        ),
    ]

    plan = generate_personalized_training_plan(
        cyclist=cyclist,
        modality=Modality.XCO,
        activities=activities,
        reference_date=date(2026, 9, 16),
    )

    assert plan.expected_aerobic_decoupling == pytest.approx(7.0)
    assert plan.aerobic_response == AerobicResponse.ELEVATED
    assert plan.load_decision == LoadDecision.REDUCE

def test_response_model_adapts_candidate_plan():
    cyclist = Cyclist(
        cyclist_id=1,
        modalities=[Modality.XCO],
        level=Level.INTERMEDIATE,
        ftp=250,
        weekly_hours=8,
        available_days=[
            "TUESDAY",
            "WEDNESDAY",
            "FRIDAY",
            "SUNDAY",
        ],
        objective=Objective.PERFORMANCE,
    )

    activities = [
        Activity(
            date=date(2026, 9, 1),
            duration_minutes=60,
            average_power=180,
            normalized_power=200,
            tss=150,
            aerobic_decoupling=1.0,
        ),
        Activity(
            date=date(2026, 9, 3),
            duration_minutes=60,
            average_power=180,
            normalized_power=200,
            tss=150,
            aerobic_decoupling=2.0,
        ),
        Activity(
            date=date(2026, 9, 7),
            duration_minutes=60,
            average_power=180,
            normalized_power=200,
            tss=155,
            aerobic_decoupling=3.0,
        ),
        Activity(
            date=date(2026, 9, 10),
            duration_minutes=60,
            average_power=180,
            normalized_power=200,
            tss=155,
        ),
    ]

    artifact = {
        "model_type": "test_response_model",
        "feature_columns": [],
        "intercept": 10.0,
        "coefficients": [],
    }

    plan = generate_personalized_training_plan(
        cyclist=cyclist,
        modality=Modality.XCO,
        activities=activities,
        reference_date=date(2026, 9, 16),
        response_model_artifact=artifact,
    )

    assert plan.expected_aerobic_decoupling == (
        pytest.approx(10.0)
    )
    assert plan.aerobic_response == (
        AerobicResponse.ELEVATED
    )
    assert plan.load_decision == LoadDecision.REDUCE
    assert plan.requested_target_tss == (
        pytest.approx(263.5)
    )
    assert plan.response_prediction_method == (
        "test_response_model"
    )

    assert plan.response_evaluated_target_tss is not None
    assert len(
        plan.workout_response_predictions
    ) == 4

    assert all(
        prediction[
            "predicted_aerobic_decoupling"
        ] == pytest.approx(10.0)
        for prediction
        in plan.workout_response_predictions
    )
