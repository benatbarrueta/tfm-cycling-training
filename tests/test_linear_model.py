import pytest

from app.data.linear_model import (
    train_linear_model,
    build_athlete_weights,
)


def test_train_linear_model_learns_simple_relationship():
    rows = [
        {
            "tss_latest": tss,
            "tss_previous": 100,
            "tss_mean_4w": 100,
            "next_week_tss": 2 * tss + 10,
        }
        for tss in [100, 200, 300, 400]
    ]

    model = train_linear_model(rows)

    prediction = model.predict([[250, 100, 100]])

    assert prediction[0] == pytest.approx(510.0)

def test_train_linear_model_raises_ValueError_error():
    with pytest.raises(ValueError):
        train_linear_model([])

def test_build_athlete_weights():
    rows = [
        {"athlete_id": "a"},
        {"athlete_id": "b"},
        {"athlete_id": "a"},
    ]

    weights = build_athlete_weights(rows)

    assert weights == pytest.approx([0.5, 1.0, 0.5])

def test_build_athlete_weights_raises_ValueError_error():
    with pytest.raises(ValueError):
        build_athlete_weights([])

def test_balancing_gives_equal_total_weight_to_each_athlete():
    rows = [
        {
            "athlete_id": athlete_id,
            "tss_latest": 100,
            "tss_previous": 100,
            "tss_mean_4w": 100,
            "next_week_tss": target,
        }
        for athlete_id, target in [
            ("a", 100),
            ("a", 100),
            ("a", 100),
            ("b", 300),
        ]
    ]

    original = train_linear_model(rows)
    balanced = train_linear_model(rows, balance_athletes=True)

    inputs = [[100, 100, 100]]

    assert original.predict(inputs)[0] == pytest.approx(150.0)
    assert balanced.predict(inputs)[0] == pytest.approx(200.0)

