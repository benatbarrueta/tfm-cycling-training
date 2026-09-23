import pytest

from app.data.evaluation import (
    calculate_mae,
    split_by_athlete,
    evaluate_persistence,
    evaluate_rolling_mean,
)


def test_calculate_mae():
    result = calculate_mae(
        actual=[200, 300, 250],
        predicted=[180, 330, 240],
    )

    assert result == pytest.approx(20.0)


@pytest.mark.parametrize(
    "actual, predicted",
    [
        ([], []),
        ([100, 200], [100]),
        ([100], []),
    ],
)
def test_calculate_mae_rejects_invalid_inputs(actual, predicted):
    with pytest.raises(ValueError):
        calculate_mae(actual, predicted)

def test_calculate_mae_is_0_when_predictions_are_perfect():
    result = calculate_mae(
        actual=[100, 200, 300],
        predicted=[100, 200, 300],
    )

    assert result == pytest.approx(0.0)

def test_split_by_athlete_keeps_athletes_separate():
    rows = [
        {"athlete_id": "a", "next_week_tss": 100},
        {"athlete_id": "b", "next_week_tss": 200},
        {"athlete_id": "a", "next_week_tss": 150},
        {"athlete_id": "c", "next_week_tss": 300},
    ]

    train, test = split_by_athlete(rows, {"b"})

    assert train == [rows[0], rows[2], rows[3]]
    assert test == [rows[1]]

    train_ids = {row["athlete_id"] for row in train}
    test_ids = {row["athlete_id"] for row in test}

    assert train_ids.isdisjoint(test_ids)

def test_split_by_athlete_returns_error_when_no_test_athletes():
    rows = [
        {"athlete_id": "a"},
        {"athlete_id": "b"},
    ]

    with pytest.raises(ValueError):
        split_by_athlete(rows, set())

def test_evaluate_persistence():
    rows = [
        {"tss_latest": 200, "next_week_tss": 250},
        {"tss_latest": 300, "next_week_tss": 250},
    ]

    assert evaluate_persistence(rows) == pytest.approx(50.0)

def test_evaluate_persistence_with_empty_list():
    with pytest.raises(ValueError):
        evaluate_persistence([])

def test_evaluate_rolling_mean():
    rows = [
        {"tss_mean_4w": 200, "next_week_tss": 250},
        {"tss_mean_4w": 300, "next_week_tss": 250},
    ]

    assert evaluate_rolling_mean(rows) == pytest.approx(50.0)

def test_evaluate_rolling_mean_with_empty_list():
    with pytest.raises(ValueError):
        evaluate_rolling_mean([])
