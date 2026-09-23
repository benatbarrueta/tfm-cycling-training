import pytest

from app.data.evaluation import (
    calculate_mae,
    split_by_athlete,
    evaluate_persistence,
    evaluate_rolling_mean,
    build_athlete_folds,
    cross_validate_by_athlete,
    is_outside_training_mean_range,
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

def test_build_athlete_folds():
    rows = [
        {"athlete_id": "a"},
        {"athlete_id": "a"},
        {"athlete_id": "b"},
        {"athlete_id": "c"},
    ]

    folds = build_athlete_folds(rows)

    assert len(folds) == 3

    validated_ids = []

    for train_fold, validation_fold in folds:
        train_ids = {row["athlete_id"] for row in train_fold}
        validation_ids = {
            row["athlete_id"] for row in validation_fold
        }

        assert len(validation_ids) == 1
        assert train_ids.isdisjoint(validation_ids)
        assert len(train_fold) + len(validation_fold) == len(rows)

        validated_ids.extend(validation_ids)

    assert sorted(validated_ids) == ["a", "b", "c"]

def test_build_athlete_folds_with_insufficient_athletes():
    rows = [
        {"athlete_id": "a"},
    ]

    with pytest.raises(ValueError):
        build_athlete_folds(rows)

def test_cross_validate_by_athlete():
    rows = [
        {
            "athlete_id": athlete_id,
            "tss_latest": tss,
            "tss_previous": 100,
            "tss_mean_4w": 100,
            "next_week_tss": 2 * tss + 10,
        }
        for athlete_id in ["a", "b"]
        for tss in [100, 200, 300]
    ]

    results = cross_validate_by_athlete(rows)

    assert len(results) == 2
    assert {result["athlete_id"] for result in results} == {"a", "b"}

    for result in results:
        assert result["n_rows"] == 3
        assert result["persistence_mae"] == pytest.approx(210.0)
        assert result["rolling_mean_mae"] == pytest.approx(310.0)
        assert result["linear_mae"] == pytest.approx(0.0, abs=1e-8)

@pytest.mark.parametrize(
    "value, expected",
    [
        (50, True),
        (100, False),
        (200, False),
        (300, False),
        (350, True),
    ],
)
def test_is_outside_training_mean_range(value, expected):
    train_rows = [
        {"tss_mean_4w": "100"},
        {"tss_mean_4w": "300"},
    ]
    row = {"tss_mean_4w": str(value)}

    result = is_outside_training_mean_range(train_rows, row)

    assert result is expected

