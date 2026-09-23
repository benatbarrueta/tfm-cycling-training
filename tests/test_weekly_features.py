import pytest

from app.data.weekly_features import (
    calculate_tss_change,
    build_tss_features,
    load_weekly_rows,
    group_rows_by_athlete,
    has_four_consecutive_weeks,
    build_feature_rows,
    build_labeled_rows,   
)   

def test_tss_increase():
    assert calculate_tss_change(200, 250) == pytest.approx(25.0)

def test_tss_decrease():
    assert calculate_tss_change(200, 150) == pytest.approx(-25.0)

def test_tss_no_change():
    assert calculate_tss_change(200, 200) == pytest.approx(0.0)

def test_tss_previous_zero():
    assert calculate_tss_change(0, 100) is None

@pytest.mark.parametrize(
    "previous_tss, current_tss",
    [
        (-100, 200),
        (200, -100),
        (-100, -200),
    ],
)
def test_negative_tss_raises_error(previous_tss, current_tss):
    with pytest.raises(ValueError):
        calculate_tss_change(previous_tss, current_tss)

def test_zero_previous_tss_does_not_hide_negative_current_tss():
    with pytest.raises(ValueError):
        calculate_tss_change(0, -100)

def test_build_tss_features():
    result = build_tss_features([100, 150, 200, 250])

    assert result == {
        "tss_latest": 250,
        "tss_previous": 200,
        "tss_mean_4w": 175.0,
        "tss_change_pct": 25.0,
    }

def test_build_tss_features_result_none():
    result = build_tss_features([100, 150, 0, 250])

    assert result["tss_change_pct"] is None

@pytest.mark.parametrize(
    "weekly_tss",
    [
        [],
        [100, 200, 300],
        [100, 200, 300, 400, 500],
    ],
)
def test_build_tss_features_requires_four_weeks(weekly_tss):
    with pytest.raises(ValueError):
        build_tss_features(weekly_tss)

@pytest.mark.parametrize("position", [0, 1, 2, 3])
def test_build_tss_features_rejects_negative_tss(position):
    weekly_tss = [100, 150, 200, 250]
    weekly_tss[position] = -10

    with pytest.raises(ValueError):
        build_tss_features(weekly_tss)

def test_load_weekly_rows(tmp_path):
    csv_path = tmp_path / "weekly.csv"
    csv_path.write_text(
        "athlete_id,week_start,weekly_tss,usable_load_week\n"
        "athlete_a,2026-01-05,150.5,True\n"
        "athlete_a,2026-01-12,,False\n",
        encoding="utf-8",
    )

    rows = load_weekly_rows(csv_path)

    assert len(rows) == 2
    assert rows[0]["weekly_tss"] == 150.5
    assert rows[0]["usable_load_week"] is True
    assert rows[1]["weekly_tss"] is None
    assert rows[1]["usable_load_week"] is False

def test_group_rows_by_athlete():
    rows = [
        {"athlete_id": "a", "week_start": "2026-01-12"},
        {"athlete_id": "b", "week_start": "2026-01-05"},
        {"athlete_id": "a", "week_start": "2026-01-05"},
    ]

    grouped = group_rows_by_athlete(rows)

    assert set(grouped) == {"a", "b"}
    assert len(grouped["a"]) == 2
    assert len(grouped["b"]) == 1

    assert [
        row["week_start"] for row in grouped["a"]
    ] == ["2026-01-05", "2026-01-12"]

    assert grouped["b"][0]["athlete_id"] == "b"

def test_group_rows_by_athlete_empty():
    grouped = group_rows_by_athlete([])

    assert grouped == {}

@pytest.mark.parametrize(
    "weeks, expected",
    [
        # Cuatro semanas consecutivas.
        (["2026-01-05", "2026-01-12", "2026-01-19", "2026-01-26"], True),
        # Falta una semana.
        (["2026-01-05", "2026-01-12", "2026-01-26", "2026-02-02"], False),
        # Una fecha repetida.
        (["2026-01-05", "2026-01-12", "2026-01-12", "2026-01-19"], False),
        # Menos de cuatro semanas.
        (["2026-01-05", "2026-01-12"], False),
        # Cruce de año.
        (["2025-12-22", "2025-12-29", "2026-01-05", "2026-01-12"], True),
    ],
)
def test_has_four_consecutive_weeks(weeks, expected):
    rows = [{"week_start": week} for week in weeks]

    assert has_four_consecutive_weeks(rows) is expected

def test_build_feature_rows_creates_two_windows():
    rows = [
        {
            "athlete_id": "a",
            "week_start": week,
            "weekly_tss": tss,
            "usable_load_week": True,
        }
        for week, tss in [
            ("2026-01-05", 100),
            ("2026-01-12", 150),
            ("2026-01-19", 200),
            ("2026-01-26", 250),
            ("2026-02-02", 300),
        ]
    ]

    result = build_feature_rows(rows)

    assert len(result) == 2

    assert result[0]["window_start"] == "2026-01-05"
    assert result[0]["window_end"] == "2026-01-26"
    assert result[0]["tss_mean_4w"] == 175.0
    assert result[0]["tss_change_pct"] == pytest.approx(25.0)

    assert result[1]["window_start"] == "2026-01-12"
    assert result[1]["window_end"] == "2026-02-02"
    assert result[1]["tss_mean_4w"] == 225.0
    assert result[1]["tss_change_pct"] == pytest.approx(20.0)

def test_build_feature_rows_with_false_usable_load():
    rows = [
        {
            "athlete_id": "a",
            "week_start": week,
            "weekly_tss": tss,
            "usable_load_week": usable,
        }
        for week, tss, usable in [
            ("2026-01-05", 100, True),
            ("2026-01-12", 150, True),
            ("2026-01-19", 200, False),
            ("2026-01-26", 250, True),
        ]
    ]

    result = build_feature_rows(rows)

    assert result == []

def test_build_feature_rows_with_none_weekly_tss():
    rows = [
        {
            "athlete_id": "a",
            "week_start": week,
            "weekly_tss": tss,
            "usable_load_week": usable,
        }
        for week, tss, usable in [
            ("2026-01-05", 100, True),
            ("2026-01-12", 150, True),
            ("2026-01-19", None, True),
            ("2026-01-26", 250, True),
        ]
    ]

    result = build_feature_rows(rows)

    assert result == []

def test_build_labeled_rows_uses_next_week():
    rows = [
        {
            "athlete_id": "a",
            "week_start": week,
            "weekly_tss": tss,
            "usable_load_week": True,
        }
        for week, tss in [
            ("2026-01-05", 100),
            ("2026-01-12", 150),
            ("2026-01-19", 200),
            ("2026-01-26", 250),
            ("2026-02-02", 400),
        ]
    ]

    result = build_labeled_rows(rows)

    assert len(result) == 1
    assert result[0]["window_end"] == "2026-01-26"
    assert result[0]["tss_latest"] == 250
    assert result[0]["tss_mean_4w"] == 175.0
    assert result[0]["target_week"] == "2026-02-02"
    assert result[0]["next_week_tss"] == 400

def test_build_labeled_rows_with_false_usable_load():
    rows = [
        {
            "athlete_id": "a",
            "week_start": week,
            "weekly_tss": tss,
            "usable_load_week": True,
        }
        for week, tss in [
            ("2026-01-05", 100),
            ("2026-01-12", 150),
            ("2026-01-19", 200),
            ("2026-01-26", 250),
            ("2026-02-09", 400),
        ]
    ]

    result = build_labeled_rows(rows)

    assert result == []

@pytest.mark.parametrize(
    "target_tss, target_usable, expected_count",
    [
        (400, False, 0),
        (None, True, 0),
        (0, True, 1),
    ],
)
def test_build_labeled_rows_validates_target(
    target_tss, target_usable, expected_count
):
    rows = [
        {
            "athlete_id": "a",
            "week_start": week,
            "weekly_tss": tss,
            "usable_load_week": True,
        }
        for week, tss in [
            ("2026-01-05", 100),
            ("2026-01-12", 150),
            ("2026-01-19", 200),
            ("2026-01-26", 250),
        ]
    ]

    rows.append({
        "athlete_id": "a",
        "week_start": "2026-02-02",
        "weekly_tss": target_tss,
        "usable_load_week": target_usable,
    })

    result = build_labeled_rows(rows)

    assert len(result) == expected_count

    if expected_count:
        assert result[0]["next_week_tss"] == 0