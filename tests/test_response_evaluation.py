import pytest

from sklearn.linear_model import LinearRegression

from app.data.response_evaluation import (
    evaluate_median_baseline,
    build_response_xy,
    train_response_linear_model,
    evaluate_response_linear_model,
    cross_validate_response_by_athlete,
    train_response_ridge_model,
    evaluate_response_ridge_model,
    cross_validate_ridge_alphas,
    train_response_random_forest,
    evaluate_response_random_forest,
    cross_validate_random_forest_configs,
    train_balanced_response_linear_model,
    evaluate_personal_median_baseline,
    cross_validate_fixed_models_by_athlete,
)

def make_response_row(
    athlete_id,
    duration,
    target,
):
    return {
        "athlete_id": athlete_id,
        "session_duration_minutes": duration,
        "session_intensity_factor": 0.75,
        "session_tss": 50,
        "previous_7d_tss": 250,
        "previous_7d_activity_count": 3,
        "previous_28d_tss": 900,
        "previous_28d_activity_count": 12,
        "target_aerobic_decoupling": target,
        "acute_chronic_load_ratio": 1.0,
        "session_to_chronic_load_ratio": 0.2,
        "previous_response_median": 7.0,
        "previous_response_count": 3,
    }

def test_evaluate_median_baseline():
    train_rows = [
        {"target_aerobic_decoupling": 2},
        {"target_aerobic_decoupling": 4},
        {"target_aerobic_decoupling": 100},
    ]

    test_rows = [
        {"target_aerobic_decoupling": 5},
        {"target_aerobic_decoupling": 10},
    ]

    result = evaluate_median_baseline(
        train_rows,
        test_rows,
    )

    assert result == pytest.approx(3.5)

def test_evaluate_median_baseline_requires_training_rows():
    with pytest.raises(ValueError):
        evaluate_median_baseline(
            [],
            [{"target_aerobic_decoupling": 5}],
        )

def test_evaluate_median_baseline_requires_test_rows():
    with pytest.raises(ValueError):
        evaluate_median_baseline(
            [{"target_aerobic_decoupling": 5}],
            [],
        )

def test_build_response_xy():
    rows = [
        {
            "session_duration_minutes": "60",
            "session_intensity_factor": "0.75",
            "session_tss": "56.25",
            "previous_7d_tss": "250",
            "previous_7d_activity_count": "3",
            "previous_28d_tss": "900",
            "previous_28d_activity_count": "12",
            "target_aerobic_decoupling": "8.5",
            "acute_chronic_load_ratio": "1.1",
            "session_to_chronic_load_ratio": "0.3",
            "previous_response_median": 7.0,
            "previous_response_count": 3,
        },
    ]

    X, y = build_response_xy(rows)

    assert X == [[
        60.0,
        0.75,
        56.25,
        250.0,
        3.0,
        900.0,
        12.0,
        1.1,
        0.3,
        7.0,
        3,
    ]]
    assert y == [8.5]

def test_build_response_xy_empty():
    X, y = build_response_xy([])

    assert X == []
    assert y == []

def test_train_response_linear_model():
    rows = [
        {
            "session_duration_minutes": duration,
            "session_intensity_factor": 0.75,
            "session_tss": 50,
            "previous_7d_tss": 250,
            "previous_7d_activity_count": 3,
            "previous_28d_tss": 900,
            "previous_28d_activity_count": 12,
            "target_aerobic_decoupling": (
                2 * duration + 1
            ),
            "acute_chronic_load_ratio": 1.0,
            "session_to_chronic_load_ratio": 0.2,
            "previous_response_median": 7.0,
            "previous_response_count": 3,
        }
        for duration in [30, 60, 90, 120]
    ]

    model = train_response_linear_model(rows)

    prediction = model.predict([[
        75,
        0.75,
        50,
        250,
        3,
        900,
        12,
        1.0,
        0.2,
        7.0,
        3,
    ]])

    assert prediction[0] == pytest.approx(151.0)

def test_train_response_linear_model_requires_rows():
    with pytest.raises(ValueError):
        train_response_linear_model([])

def test_evaluate_response_linear_model():
    train_rows = [
        {
            "session_duration_minutes": duration,
            "session_intensity_factor": 0.75,
            "session_tss": 50,
            "previous_7d_tss": 250,
            "previous_7d_activity_count": 3,
            "previous_28d_tss": 900,
            "previous_28d_activity_count": 12,
            "target_aerobic_decoupling": (
                2 * duration + 1
            ),
            "acute_chronic_load_ratio": 1.0,
            "session_to_chronic_load_ratio": 0.2,
            "previous_response_median": 7.0,
            "previous_response_count": 3,
        }
        for duration in [30, 60, 90, 120]
    ]

    test_rows = [
        {
            "session_duration_minutes": 75,
            "session_intensity_factor": 0.75,
            "session_tss": 50,
            "previous_7d_tss": 250,
            "previous_7d_activity_count": 3,
            "previous_28d_tss": 900,
            "previous_28d_activity_count": 12,
            "target_aerobic_decoupling": 150,
            "acute_chronic_load_ratio": 1.0,
            "session_to_chronic_load_ratio": 0.2,
            "previous_response_median": 7.0,
            "previous_response_count": 3,
        },
    ]

    model = train_response_linear_model(
        train_rows
    )

    result = evaluate_response_linear_model(
        model,
        test_rows,
    )

    assert result == pytest.approx(1.0)

def test_evaluate_response_linear_model_requires_test_rows():
    model = LinearRegression()

    with pytest.raises(ValueError):
        evaluate_response_linear_model(
            model,
            [],
        )

def test_cross_validate_response_by_athlete():
    rows = [
        make_response_row("athlete-a", 30, 5),
        make_response_row("athlete-a", 60, 7),
        make_response_row("athlete-b", 45, 6),
        make_response_row("athlete-b", 75, 8),
    ]

    results = cross_validate_response_by_athlete(
        rows
    )

    assert len(results) == 2
    assert {
        result["athlete_id"]
        for result in results
    } == {
        "athlete-a",
        "athlete-b",
    }

    for result in results:
        assert result["n_rows"] == 2
        assert result["median_mae"] >= 0
        assert result["linear_mae"] >= 0
        assert result["balanced_linear_mae"] >= 0
        assert result["personal_median_mae"] >= 0

def test_train_and_evaluate_response_ridge_model():
    train_rows = [
        make_response_row(
            "athlete-a",
            duration,
            2 * duration + 1,
        )
        for duration in [30, 60, 90, 120]
    ]

    test_rows = [
        make_response_row(
            "athlete-b",
            75,
            150,
        ),
    ]

    model = train_response_ridge_model(
        train_rows,
        alpha=0.01,
    )

    result = evaluate_response_ridge_model(
        model,
        test_rows,
    )

    assert result < 2.0

def test_train_response_ridge_model_validates_input():
    with pytest.raises(ValueError):
        train_response_ridge_model([])

    rows = [
        make_response_row(
            "athlete-a",
            60,
            8,
        ),
    ]

    with pytest.raises(ValueError):
        train_response_ridge_model(
            rows,
            alpha=0,
        )

def test_evaluate_response_ridge_model_requires_rows():
    model = train_response_ridge_model([
        make_response_row(
            "athlete-a",
            60,
            8,
        ),
    ])

    with pytest.raises(ValueError):
        evaluate_response_ridge_model(
            model,
            [],
        )

def test_cross_validate_ridge_alphas():
    rows = [
        make_response_row("athlete-a", 30, 5),
        make_response_row("athlete-a", 60, 7),
        make_response_row("athlete-b", 45, 6),
        make_response_row("athlete-b", 75, 8),
    ]

    results = cross_validate_ridge_alphas(
        rows,
        (0.1, 1.0, 10.0),
    )

    assert [
        result["alpha"]
        for result in results
    ] == [
        0.1,
        1.0,
        10.0,
    ]

    for result in results:
        assert result["mean_athlete_mae"] >= 0
        assert result["fold_count"] == 2

def test_cross_validate_ridge_alphas_requires_alpha():
    rows = [
        make_response_row(
            "athlete-a",
            60,
            8,
        ),
        make_response_row(
            "athlete-b",
            75,
            9,
        ),
    ]

    with pytest.raises(ValueError):
        cross_validate_ridge_alphas(
            rows,
            (),
        )

def test_train_and_evaluate_response_random_forest():
    train_rows = [
        make_response_row(
            "athlete-a",
            duration,
            5 if duration < 60 else 15,
        )
        for duration in [
            30,
            40,
            50,
            70,
            80,
            90,
        ]
    ]

    test_rows = [
        make_response_row(
            "athlete-b",
            45,
            5,
        ),
        make_response_row(
            "athlete-b",
            75,
            15,
        ),
    ]

    model = train_response_random_forest(
        train_rows,
        n_estimators=50,
        min_samples_leaf=1,
    )

    result = evaluate_response_random_forest(
        model,
        test_rows,
    )

    assert result < 3.0

def test_train_response_random_forest_validates_input():
    with pytest.raises(ValueError):
        train_response_random_forest([])

    rows = [
        make_response_row(
            "athlete-a",
            60,
            8,
        ),
    ]

    with pytest.raises(ValueError):
        train_response_random_forest(
            rows,
            n_estimators=0,
        )

    with pytest.raises(ValueError):
        train_response_random_forest(
            rows,
            min_samples_leaf=0,
        )

def test_evaluate_response_random_forest_requires_rows():
    model = train_response_random_forest(
        [
            make_response_row(
                "athlete-a",
                60,
                8,
            ),
        ],
        n_estimators=10,
        min_samples_leaf=1,
    )

    with pytest.raises(ValueError):
        evaluate_response_random_forest(
            model,
            [],
        )

def test_cross_validate_random_forest_configs():
    rows = [
        make_response_row("athlete-a", 30, 5),
        make_response_row("athlete-a", 60, 7),
        make_response_row("athlete-b", 45, 6),
        make_response_row("athlete-b", 75, 8),
    ]

    results = cross_validate_random_forest_configs(
        rows,
        (
            (3, 1),
            (None, 1),
        ),
        n_estimators=10,
    )

    assert len(results) == 2

    assert results[0]["max_depth"] == 3
    assert results[0]["min_samples_leaf"] == 1

    assert results[1]["max_depth"] is None
    assert results[1]["min_samples_leaf"] == 1

    for result in results:
        assert result["mean_athlete_mae"] >= 0
        assert result["fold_count"] == 2

def test_cross_validate_random_forest_requires_configs():
    rows = [
        make_response_row("athlete-a", 30, 5),
        make_response_row("athlete-b", 45, 6),
    ]

    with pytest.raises(ValueError):
        cross_validate_random_forest_configs(
            rows,
            (),
            n_estimators=10,
        )

def test_train_balanced_response_linear_model():
    rows = [
        make_response_row(
            "athlete-a",
            30,
            61,
        ),
        make_response_row(
            "athlete-a",
            60,
            121,
        ),
        make_response_row(
            "athlete-b",
            90,
            181,
        ),
        make_response_row(
            "athlete-b",
            120,
            241,
        ),
    ]

    model = train_balanced_response_linear_model(
        rows
    )

    prediction = model.predict([[
        75,
        0.75,
        50,
        250,
        3,
        900,
        12,
        1.0,
        0.2,
        7.0,
        3,
    ]])

    assert prediction[0] == pytest.approx(151.0)

def test_train_balanced_response_linear_model_requires_rows():
    with pytest.raises(ValueError):
        train_balanced_response_linear_model([])

def test_evaluate_personal_median_baseline():
    rows = [
        {
            "target_aerobic_decoupling": 8,
            "previous_response_median": 6,
        },
        {
            "target_aerobic_decoupling": 12,
            "previous_response_median": 9,
        },
    ]

    result = evaluate_personal_median_baseline(
        rows
    )

    assert result == pytest.approx(2.5)

def test_evaluate_personal_median_baseline_requires_rows():
    with pytest.raises(ValueError):
        evaluate_personal_median_baseline([])

def test_cross_validate_fixed_models_by_athlete():
    rows = [
        make_response_row("athlete-a", 30, 5),
        make_response_row("athlete-a", 60, 7),
        make_response_row("athlete-b", 45, 6),
        make_response_row("athlete-b", 75, 8),
    ]

    results = cross_validate_fixed_models_by_athlete(
        rows,
        ridge_alpha=1.0,
        forest_min_samples_leaf=1,
        forest_n_estimators=10,
    )

    assert len(results) == 2

    for result in results:
        assert result["n_rows"] == 2
        assert result["global_median_mae"] >= 0
        assert result["personal_median_mae"] >= 0
        assert result["linear_mae"] >= 0
        assert result["balanced_linear_mae"] >= 0
        assert result["ridge_mae"] >= 0
        assert result["forest_mae"] >= 0
