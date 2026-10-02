from datetime import date

import pytest

from app.models.activity import Activity
from app.models.workout import Workout, WorkoutType
from app.models.aerobic_response import AerobicResponse
from app.models.training_plan import TrainingPlan

from app.services.response_prediction_service import (
    build_candidate_response_features,
    calculate_workout_date,
    calculate_workout_intensity_factor,
    predict_training_plan_responses,
    summarize_plan_response_predictions,
)

def make_activity(
    activity_date: date,
    tss: float,
    response: float | None = None,
) -> Activity:
    return Activity(
        date=activity_date,
        duration_minutes=None,
        average_power=None,
        normalized_power=None,
        tss=tss,
        aerobic_decoupling=response,
    )

def test_calculate_workout_date():
    result = calculate_workout_date(
        reference_date=date(2026, 1, 28),
        day="FRIDAY",
    )

    assert result == date(2026, 1, 30)

def test_calculate_workout_intensity_factor():
    workout = Workout(
        day="TUESDAY",
        workout_type=WorkoutType.ENDURANCE,
        target_tss=64,
        estimated_tss=64,
        duration_minutes=60,
    )

    result = calculate_workout_intensity_factor(
        workout
    )

    assert result == pytest.approx(0.8)

def test_build_candidate_response_features():
    activities = [
        make_activity(
            date(2025, 12, 15),
            30,
            2.0,
        ),
        make_activity(
            date(2026, 1, 5),
            40,
            4.0,
        ),
        make_activity(
            date(2026, 1, 20),
            40,
            6.0,
        ),
        make_activity(
            date(2026, 1, 25),
            50,
            None,
        ),
    ]

    workout = Workout(
        day="THURSDAY",
        workout_type=WorkoutType.ENDURANCE,
        target_tss=64,
        estimated_tss=64,
        duration_minutes=60,
    )

    result = build_candidate_response_features(
        workout,
        session_date=date(2026, 1, 29),
        activities=activities,
        ftp=250,
    )

    assert result is not None
    assert result[
        "session_duration_minutes"
    ] == pytest.approx(60)
    assert result[
        "session_intensity_factor"
    ] == pytest.approx(0.8)
    assert result["session_tss"] == pytest.approx(64)
    assert result["previous_7d_tss"] == pytest.approx(50)
    assert result[
        "previous_7d_activity_count"
    ] == 1
    assert result["previous_28d_tss"] == pytest.approx(130)
    assert result[
        "previous_28d_activity_count"
    ] == 3
    assert result[
        "previous_response_median"
    ] == pytest.approx(4.0)
    assert result[
        "previous_response_count"
    ] == 3

def test_candidate_features_require_response_history():
    activities = [
        make_activity(
            date(2026, 1, 20),
            40,
            4.0,
        ),
        make_activity(
            date(2026, 1, 25),
            50,
            6.0,
        ),
    ]

    workout = Workout(
        day="THURSDAY",
        workout_type=WorkoutType.ENDURANCE,
        target_tss=64,
        estimated_tss=64,
        duration_minutes=60,
    )

    result = build_candidate_response_features(
        workout,
        session_date=date(2026, 1, 29),
        activities=activities,
        ftp=250,
    )

    assert result is None

def test_predict_training_plan_responses_accumulates_planned_load():
    activities = [
        make_activity(
            date(2025, 12, 15),
            30,
            2.0,
        ),
        make_activity(
            date(2026, 1, 5),
            40,
            4.0,
        ),
        make_activity(
            date(2026, 1, 19),
            40,
            6.0,
        ),
        make_activity(
            date(2026, 1, 25),
            50,
            None,
        ),
    ]

    plan = TrainingPlan(
        target_tss=100,
        workouts=[
            Workout(
                day="TUESDAY",
                workout_type=WorkoutType.ENDURANCE,
                target_tss=50,
                estimated_tss=50,
                duration_minutes=60,
            ),
            Workout(
                day="THURSDAY",
                workout_type=WorkoutType.ENDURANCE,
                target_tss=50,
                estimated_tss=50,
                duration_minutes=60,
            ),
        ],
    )

    artifact = {
        "feature_columns": [
            "previous_7d_tss",
        ],
        "intercept": 0.0,
        "coefficients": [
            0.1,
        ],
    }

    result = predict_training_plan_responses(
        plan,
        reference_date=date(2026, 1, 26),
        activities=activities,
        ftp=250,
        artifact=artifact,
    )

    assert len(result) == 2

    assert result[0][
        "predicted_aerobic_decoupling"
    ] == pytest.approx(5.0)
    assert result[0][
        "aerobic_response"
    ] == AerobicResponse.STABLE

    assert result[1][
        "predicted_aerobic_decoupling"
    ] == pytest.approx(10.0)
    assert result[1][
        "aerobic_response"
    ] == AerobicResponse.ELEVATED

    assert result[0]["features"][
        "previous_7d_tss"
    ] == pytest.approx(50)

    assert result[1]["features"][
        "previous_7d_tss"
    ] == pytest.approx(100)

def test_summarize_plan_response_predictions():
    predictions = [
        {
            "predicted_aerobic_decoupling": 3.0,
        },
        {
            "predicted_aerobic_decoupling": 7.0,
        },
        {
            "predicted_aerobic_decoupling": 4.0,
        },
    ]

    expected, response = (
        summarize_plan_response_predictions(
            predictions
        )
    )

    assert expected == pytest.approx(7.0)
    assert response == AerobicResponse.ELEVATED

def test_summarize_plan_response_predictions_unknown():
    predictions = [
        {
            "predicted_aerobic_decoupling": None,
        },
    ]

    expected, response = (
        summarize_plan_response_predictions(
            predictions
        )
    )

    assert expected is None
    assert response == AerobicResponse.UNKNOWN

def test_summarize_plan_response_predictions_stable():
    predictions = [
        {
            "predicted_aerobic_decoupling": -2.0,
        },
        {
            "predicted_aerobic_decoupling": 5.0,
        },
    ]

    expected, response = (
        summarize_plan_response_predictions(
            predictions
        )
    )

    assert expected == pytest.approx(5.0)
    assert response == AerobicResponse.STABLE
