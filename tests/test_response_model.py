import pytest

from app.data.response_evaluation import FEATURE_COLUMNS
from app.data.response_model import (
    load_response_model_artifact,
    predict_response_from_artifact,
    save_response_model_artifact,
    train_response_model_artifact,
)

def make_model_row(
    athlete_id: str,
    duration: float,
) -> dict:
    row = {
        column: 0.0
        for column in FEATURE_COLUMNS
    }

    row["athlete_id"] = athlete_id
    row["session_duration_minutes"] = duration
    row["target_aerobic_decoupling"] = (
        2 * duration + 1
    )

    return row

def test_train_and_predict_response_model_artifact():
    rows = [
        make_model_row("athlete-a", 1),
        make_model_row("athlete-a", 2),
        make_model_row("athlete-b", 3),
        make_model_row("athlete-b", 4),
    ]

    artifact = train_response_model_artifact(
        rows
    )

    features = {
        column: 0.0
        for column in FEATURE_COLUMNS
    }
    features["session_duration_minutes"] = 5

    prediction = predict_response_from_artifact(
        artifact,
        features,
    )

    assert artifact["model_type"] == (
        "balanced_linear_regression"
    )
    assert artifact["training_rows"] == 4
    assert artifact["training_athletes"] == 2
    assert prediction == pytest.approx(11.0)

def test_response_model_artifact_round_trip(
    tmp_path,
):
    artifact = {
        "model_type": "balanced_linear_regression",
        "target": "calculated_aerobic_decoupling",
        "feature_columns": [
            "session_tss",
        ],
        "intercept": 1.0,
        "coefficients": [
            0.5,
        ],
        "training_rows": 100,
        "training_athletes": 10,
        "athlete_weighting": "equal_total_weight",
    }

    output = tmp_path / "models" / "response.json"

    save_response_model_artifact(
        artifact,
        output,
    )

    loaded = load_response_model_artifact(
        output
    )

    prediction = predict_response_from_artifact(
        loaded,
        {
            "session_tss": 10,
        },
    )

    assert loaded == artifact
    assert prediction == pytest.approx(6.0)

def test_predict_response_rejects_missing_feature():
    artifact = {
        "feature_columns": [
            "session_tss",
        ],
        "intercept": 1.0,
        "coefficients": [
            0.5,
        ],
    }

    with pytest.raises(
        ValueError,
        match="Falta la variable session_tss",
    ):
        predict_response_from_artifact(
            artifact,
            {},
        )
