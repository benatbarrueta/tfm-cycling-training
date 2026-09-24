from app.data.ml_dataset import build_xy, VOLUME_FEATURE_COLUMNS


def test_build_xy():
    rows = [{
        "athlete_id": "a",
        "window_end": "2026-01-26",
        "tss_latest": "250",
        "tss_previous": "200",
        "tss_mean_4w": "175",
        "next_week_tss": "300",
    }]

    X, y = build_xy(rows)

    assert X == [[250.0, 200.0, 175.0]]
    assert y == [300.0]

def test_build_xy_multiple_rows():
    rows = [
        {
            "athlete_id": "a",
            "window_end": "2026-01-26",
            "tss_latest": "250",
            "tss_previous": "200",
            "tss_mean_4w": "175",
            "next_week_tss": "300",
        },
        {
            "athlete_id": "b",
            "window_end": "2026-01-26",
            "tss_latest": "150",
            "tss_previous": "100",
            "tss_mean_4w": "125",
            "next_week_tss": "200",
        },
    ]

    X, y = build_xy(rows)

    assert X == [[250.0, 200.0, 175.0], [150.0, 100.0, 125.0]]
    assert y == [300.0, 200.0]

def test_build_xy_with_volume_features():
    rows = [{
        "tss_latest": "250",
        "tss_previous": "200",
        "tss_mean_4w": "175",
        "hours_latest": "5",
        "hours_mean_4w": "3.5",
        "activities_latest": "6",
        "activities_mean_4w": "4.5",
        "training_days_latest": "4",
        "training_days_mean_4w": "2.75",
        "next_week_tss": "300",
    }]

    X, y = build_xy(
        rows,
        feature_columns=VOLUME_FEATURE_COLUMNS,
    )

    assert X == [[250, 200, 175, 5, 3.5, 6, 4.5, 4, 2.75]]
    assert y == [300]
    