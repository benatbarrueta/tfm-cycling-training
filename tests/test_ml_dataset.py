from app.data.ml_dataset import build_xy


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