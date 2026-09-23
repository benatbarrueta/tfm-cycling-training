import json

import pytest

from app.data.goldencheetah import import_athlete, metric, weekly_table


def ride(day, tss="50", duration="3600", sport="Bike"):
    return {"date": f"2020/01/{day:02} 12:00:00 UTC", "sport": sport,
            "METRICS": {"workout_time": duration, "coggan_tss": tss,
                        "coggan_np": ["200", "3600"]}}


def load(tmp_path, rides):
    path = tmp_path / "athlete.json"
    path.write_text(json.dumps({"ATHLETE": {"id": "{a}"}, "RIDES": rides}))
    return import_athlete(path)


@pytest.mark.parametrize("raw,expected", [("12.3", 12.3), (["200", "3600"], 200),
    ("0", 0), (None, None), ("-255", None), ("nan", None), ("inf", None),
    ([], None), ([1, 2, 3], None), (True, None)])
def test_metric(raw, expected):
    assert metric(raw) == expected


def test_import_filters_audits_and_deduplicates(tmp_path):
    rows, audit = load(tmp_path, [ride(6), ride(6), ride(7, sport="Run"),
                                {"sport": "Bike", "date": "invalid"}, ride(8, duration="12")])
    assert len(rows) == 2
    assert rows[0]["normalized_power"] == 200
    assert rows[0]["week_start"] == "2020-01-06"
    assert "duration_review" in rows[1]["quality_flags"]
    assert audit["duplicates"] == audit["skipped_non_bike"] == audit["invalid_dates"] == 1


def test_conflicting_duplicates_rejected(tmp_path):
    with pytest.raises(ValueError, match="Conflicting"):
        load(tmp_path, [ride(6), ride(6, tss="70")])


def test_missing_tss_does_not_become_zero_or_complete_load(tmp_path):
    rows, _ = load(tmp_path, [ride(1), ride(6), ride(7, tss=None), ride(20)])
    weeks = weekly_table(rows)
    assert weeks[1]["observed_tss"] == 50
    assert weeks[1]["tss_coverage"] == 0.5
    assert weeks[1]["weekly_tss"] is None
    assert weeks[2]["no_records"]
    assert weeks[2]["observed_tss"] is None
    assert weeks[0]["boundary_week"] and weeks[-1]["boundary_week"]


def test_usable_week_and_duration_review(tmp_path):
    rows, _ = load(tmp_path, [ride(1), ride(6), ride(7, tss="0"),
                             ride(13, duration="168914"), ride(20)])
    weeks = weekly_table(rows)
    assert weeks[1]["weekly_tss"] == 50
    assert weeks[1]["training_days"] == 2
    assert weeks[1]["observed_duration_minutes"] == 120
    assert weeks[2]["duration_review"]
    assert weeks[2]["weekly_tss"] is None
    other = [dict(r, athlete_id="b") for r in rows]
    assert len(weekly_table(rows + other)) == 2 * len(weeks)
