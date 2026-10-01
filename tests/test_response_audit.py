import pytest
import json
import zipfile

from datetime import datetime

from app.data.response_audit import (
    has_power_and_heart_rate,
    summarize_response_candidates,
    audit_athlete_summary,
    summarize_signal_coverage,
    read_activity_samples,
    audit_activity_csv,
    list_activity_csvs,
    read_athlete_summary,
    parse_csv_datetime,
    find_csv_candidates,
    find_best_hour_offset,
    summarize_activity_offsets,
    build_csv_datetime_index,
    find_nearest_csv,
    collect_unmatched_examples,
    match_activity_csv,
    calculate_signal_coverage,
    audit_athlete_signal_coverage,
    summarize_time_axis,
    summarize_activity_signal_quality,
    longest_continuous_paired_segment_seconds,
)


@pytest.mark.parametrize(
    "metrics, expected",
    [
        (
            {
                "average_power": ["200", "3600"],
                "average_hr": ["145", "3600"],
            },
            True,
        ),
        ({"average_power": "200", "average_hr": "145"}, True),
        ({"average_power": "200"}, False),
        ({"average_hr": "145"}, False),
        ({"average_power": "0", "average_hr": "145"}, False),
        ({"average_power": "200", "average_hr": "-255"}, False),
        ({}, False),
    ],
)
def test_has_power_and_heart_rate(metrics, expected):
    ride = {"METRICS": metrics}

    assert has_power_and_heart_rate(ride) is expected

def test_empty_activity_returns_false():
    ride = {}
    assert has_power_and_heart_rate(ride) is False

def test_summarize_response_candidates():
    rides = [
        {
            "sport": "Bike",
            "METRICS": {
                "average_power": "200",
                "average_hr": "145",
            },
        },
        {
            "sport": "Bike",
            "METRICS": {"average_power": "180"},
        },
        {
            "sport": "Run",
            "METRICS": {
                "average_power": "250",
                "average_hr": "150",
            },
        },
    ]

    result = summarize_response_candidates(rides)

    assert result == {
        "total_activities": 3,
        "cycling_activities": 2,
        "response_candidates": 1,
        "cycling_without_required_metrics": 1,
    }

def test_audit_athlete_summary(tmp_path):
    path = tmp_path / "athlete.json"

    data = {
        "ATHLETE": {"id": "{athlete-a}"},
        "RIDES": [
            {
                "sport": "Bike",
                "METRICS": {
                    "average_power": ["200", "3600"],
                    "average_hr": ["145", "3600"],
                },
            },
            {
                "sport": "Bike",
                "METRICS": {},
            },
        ],
    }

    path.write_text(
        json.dumps(data),
        encoding="utf-8-sig",
    )

    result = audit_athlete_summary(path)

    assert result == {
        "athlete_id": "athlete-a",
        "total_activities": 2,
        "cycling_activities": 2,
        "response_candidates": 1,
        "cycling_without_required_metrics": 1,
    }

def test_summarize_signal_coverage():
    samples = [
        {"power": "200", "hr": "145"},  # Válida.
        {"power": "0", "hr": "120"},    # Sin pedalear, pero válida.
        {"power": "", "hr": "140"},     # Falta potencia.
        {"power": "180", "hr": ""},     # Falta FC.
        {"power": "180", "hr": "0"},    # FC inválida.
        {"power": "-10", "hr": "140"},  # Potencia inválida.
    ]

    result = summarize_signal_coverage(samples)

    assert result == {
        "total_samples": 6,
        "paired_samples": 2,
    }

def test_read_activity_samples(tmp_path):
    zip_path = tmp_path / "athlete.zip"

    with zipfile.ZipFile(zip_path, "w") as archive:
        archive.writestr(
            "ride.csv",
            "secs,power,hr\n0,200,145\n1,210,146\n",
        )

    with zipfile.ZipFile(zip_path) as archive:
        samples = read_activity_samples(
            archive,
            "ride.csv",
        )

    assert samples == [
        {"secs": "0", "power": "200", "hr": "145"},
        {"secs": "1", "power": "210", "hr": "146"},
    ]

def test_audit_activity_csv(tmp_path):
    zip_path = tmp_path / "athlete.zip"
    csv_name = "activities/ride.csv"

    csv_content = (
        "secs,power,hr\n"
        "0,200,145\n"
        "1,0,120\n"
        "2,,140\n"
        "3,180,0\n"
    )

    with zipfile.ZipFile(zip_path, "w") as archive:
        archive.writestr(csv_name, csv_content)

    result = audit_activity_csv(zip_path, csv_name)

    assert result == {
        "total_samples": 4,
        "paired_samples": 2,
    }

def test_audit_activity_without_hr_csv_throws_error(tmp_path):
    zip_path = tmp_path / "athlete.zip"
    csv_name = "activities/ride.csv"

    csv_content = (
        "secs,power\n"
        "0,200\n"
        "1,0\n"
        "2,\n"
        "3,180\n"
    )

    with zipfile.ZipFile(zip_path, "w") as archive:
        archive.writestr(csv_name, csv_content)

    with pytest.raises(ValueError):
        audit_activity_csv(zip_path, csv_name)

def test_list_activity_csvs(tmp_path):
    zip_path = tmp_path / "athlete.zip"

    with zipfile.ZipFile(zip_path, "w") as archive:
        archive.writestr("activities/b.csv", "")
        archive.writestr("activities/a.CSV", "")
        archive.writestr("summary.json", "{}")
        archive.writestr("__MACOSX/._b.csv", "")

    result = list_activity_csvs(zip_path)

    assert result == [
        "activities/a.CSV",
        "activities/b.csv",
    ]

def test_list_activity_csvs_empty_zip(tmp_path):
    zip_path = tmp_path / "athlete.zip"

    with zipfile.ZipFile(zip_path, "w") as archive:
        archive.writestr("summary.json", "{}")

    result = list_activity_csvs(zip_path)

    assert result == []

def test_read_athlete_summary_from_zip(tmp_path):
    zip_path = tmp_path / "athlete.zip"

    data = {
        "ATHLETE": {"id": "{athlete-a}"},
        "RIDES": [],
    }

    with zipfile.ZipFile(zip_path, "w") as archive:
        archive.writestr(
            "athlete/summary.json",
            json.dumps(data).encode("utf-8-sig"),
        )
        archive.writestr("__MACOSX/._summary.json", "{}")

    result = read_athlete_summary(zip_path)

    assert result == data

def test_parse_csv_datetime():
    result = parse_csv_datetime(
        "activities/2017_02_19_15_02_55.csv"
    )

    assert result == datetime(2017, 2, 19, 15, 2, 55)
    assert result.tzinfo is None

def test_parse_csv_datetime_invalid_format():
    with pytest.raises(ValueError):
        parse_csv_datetime("activities/invalid_format.csv")

def test_find_csv_candidates_with_offset():
    csv_names = [
        "activities/2017_02_19_15_02_55.csv",
        "activities/2017_02_19_14_02_55.csv",
        "activities/summary.csv",
    ]

    result = find_csv_candidates(
        "2017/02/19 14:02:55 UTC",
        csv_names,
        offset_minutes=60,
    )

    assert result == [
        "activities/2017_02_19_15_02_55.csv",
    ]

def test_find_csv_candidates_without_match():
    result = find_csv_candidates(
        "2017/02/19 14:02:55 UTC",
        ["2017_02_19_15_02_55.csv"],
        offset_minutes=120,
    )

    assert result == []

def test_find_csv_candidates_returns_ambiguous_matches():
    csv_names = [
        "first/2017_02_19_15_02_55.csv",
        "second/2017_02_19_15_02_55.csv",
    ]

    result = find_csv_candidates(
        "2017/02/19 14:02:55 UTC",
        csv_names,
        offset_minutes=60,
    )

    assert result == sorted(csv_names)

def test_find_best_hour_offset():
    rides = [
        {
            "sport": "Bike",
            "date": "2017/02/19 14:02:55 UTC",
        },
        {
            "sport": "Bike",
            "date": "2017/02/20 08:00:00 UTC",
        },
    ]

    csv_names = [
        "2017_02_19_15_02_55.csv",
        "2017_02_20_09_00_00.csv",
    ]

    result = find_best_hour_offset(rides, csv_names)

    assert result == {
        "offset_minutes": 60,
        "unique_matches": 2,
        "missing_matches": 0,
        "ambiguous_matches": 0,
    }

def test_empty_list():
    rides = []
    csv_names = []

    with pytest.raises(ValueError):
        find_best_hour_offset(rides, csv_names)

def test_summarize_activity_offsets_counts_unique_bike_matches():
    rides = [
        {
            "sport": "Bike",
            "date": "2017/02/19 14:02:55 UTC",
        },
        {
            "sport": "Bike",
            "date": "2017/02/20 08:00:00 UTC",
        },
        {
            "sport": "Run",
            "date": "2017/02/21 10:00:00 UTC",
        },
    ]

    csv_names = [
        "2017_02_19_15_02_55.csv",
        "2017_02_20_10_00_00.csv",
    ]

    result = summarize_activity_offsets(rides, csv_names)

    assert result == {
        "offset_counts": {60: 1, 120: 1},
        "matched_activities": 2,
        "unmatched_activities": 0,
        "ambiguous_activities": 0,
    }

def test_build_csv_datetime_index():
    csv_names = [
        "second/2017_02_19_15_02_55.csv",
        "first/2017_02_19_15_02_55.csv",
        "2017_02_20_09_00_00.csv",
        "summary.csv",
    ]

    result = build_csv_datetime_index(csv_names)

    assert result == {
        datetime(2017, 2, 19, 15, 2, 55): [
            "first/2017_02_19_15_02_55.csv",
            "second/2017_02_19_15_02_55.csv",
        ],
        datetime(2017, 2, 20, 9, 0, 0): [
            "2017_02_20_09_00_00.csv",
        ],
    }

def test_build_csv_datetime_index_empty():
    assert build_csv_datetime_index([]) == {}

def test_summarize_activity_offsets_counts_ambiguity_once():
    rides = [{
        "sport": "Bike",
        "date": "2017/02/19 14:02:55 UTC",
    }]

    csv_names = [
        "first/2017_02_19_15_02_55.csv",
        "second/2017_02_19_15_02_55.csv",
    ]

    result = summarize_activity_offsets(rides, csv_names)

    assert result == {
        "offset_counts": {},
        "matched_activities": 0,
        "unmatched_activities": 0,
        "ambiguous_activities": 1,
    }

def test_find_nearest_csv():
    result = find_nearest_csv(
        "2017/02/19 14:02:55 UTC",
        [
            "2017_02_19_15_02_55.csv",
            "2017_02_20_09_00_00.csv",
        ],
    )

    assert result == (
        "2017_02_19_15_02_55.csv",
        60.0,
    )

def test_find_nearest_csv_empty():
    assert find_nearest_csv(
        "2017/02/19 14:02:55 UTC",
        [],
    ) is None

def test_collect_unmatched_examples():
    rides = [
        {
            "sport": "Bike",
            "date": "2017/02/19 14:02:55 UTC",
        },
        {
            "sport": "Bike",
            "date": "2017/02/20 08:00:30 UTC",
        },
    ]

    csv_names = [
        "2017_02_19_15_02_55.csv",
        "2017_02_20_09_00_00.csv",
    ]

    result = collect_unmatched_examples(
        rides,
        csv_names,
    )

    assert result == [{
        "ride_date_utc": "2017/02/20 08:00:30 UTC",
        "nearest_csv": "2017_02_20_09_00_00.csv",
        "difference_minutes": pytest.approx(59.5),
    }]

def test_collect_unmatched_examples_limit0():
    with pytest.raises(ValueError, match="El límite debe ser mayor que cero."):
        collect_unmatched_examples([], [], limit=0)

def test_match_activity_csv():
    index = build_csv_datetime_index([
        "2017_10_17_16_43_50.csv",
    ])

    result = match_activity_csv(
        "2017/10/17 06:13:50 UTC",
        index,
    )

    assert result == {
        "status": "matched",
        "csv_name": "2017_10_17_16_43_50.csv",
        "offset_minutes": 630,
    }

def test_match_activity_csv_missing():
    result = match_activity_csv(
        "2017/10/17 06:13:50 UTC",
        {},
    )

    assert result == {
        "status": "missing",
        "csv_name": None,
        "offset_minutes": None,
    }

def test_match_activity_csv_ambiguous():
    index = build_csv_datetime_index([
        "first/2017_10_17_16_43_50.csv",
        "second/2017_10_17_16_43_50.csv",
    ])

    result = match_activity_csv(
        "2017/10/17 06:13:50 UTC",
        index,
    )

    assert result["status"] == "ambiguous"
    assert result["csv_name"] is None

def test_calculate_signal_coverage():
    samples = [
        {"power": "200", "hr": "145"},
        {"power": "0", "hr": "120"},
        {"power": "", "hr": "140"},
        {"power": "180", "hr": "0"},
    ]

    assert calculate_signal_coverage(samples) == pytest.approx(0.5)

def test_calculate_signal_coverage_empty():
    assert calculate_signal_coverage([]) is None

def test_audit_athlete_signal_coverage_requires_zip(tmp_path):
    path = tmp_path / "athlete.json"
    path.write_text("{}", encoding="utf-8")

    with pytest.raises(ValueError):
        audit_athlete_signal_coverage(path)

def test_summarize_time_axis():
    samples = [
        {"secs": "0"},
        {"secs": "1"},
        {"secs": "2"},
        {"secs": "10"},
        {"secs": "9"},
        {"secs": ""},
    ]

    result = summarize_time_axis(samples)

    assert result == {
        "valid_time_samples": 5,
        "invalid_time_samples": 1,
        "elapsed_seconds": 9,
        "non_increasing_steps": 1,
        "gaps_over_5_seconds": 1,
        "max_gap_seconds": 8,
    }

def test_summarize_time_axis_empty_list():
    result = summarize_time_axis([])

    assert result == {
        "valid_time_samples": 0,
        "invalid_time_samples": 0,
        "elapsed_seconds": None,
        "non_increasing_steps": 0,
        "gaps_over_5_seconds": 0,
        "max_gap_seconds": None,
    }

def test_summarize_activity_signal_quality():
    samples = [
        {"secs": "0", "power": "200", "hr": "140"},
        {"secs": "1", "power": "0", "hr": "141"},
        {"secs": "10", "power": "", "hr": "142"},
    ]

    result = summarize_activity_signal_quality(samples)

    assert result == {
        "signal_coverage": pytest.approx(2 / 3),
        "valid_time_samples": 3,
        "invalid_time_samples": 0,
        "elapsed_seconds": 10,
        "non_increasing_steps": 0,
        "gaps_over_5_seconds": 1,
        "max_gap_seconds": 9,
    }

def test_longest_continuous_paired_segment_seconds():
    samples = [
        {"secs": "0", "power": "200", "hr": "140"},
        {"secs": "1", "power": "210", "hr": "141"},
        {"secs": "2", "power": "", "hr": "142"},
        {"secs": "4", "power": "220", "hr": "143"},
        {"secs": "10", "power": "230", "hr": "144"},
        {"secs": "11", "power": "240", "hr": "145"},
    ]

    result = longest_continuous_paired_segment_seconds(
        samples,
        max_gap_seconds=5,
    )

    assert result == 4

def test_longest_continuous_segment_rejects_invalid_gap():
    with pytest.raises(ValueError):
        longest_continuous_paired_segment_seconds(
            [],
            max_gap_seconds=0,
        )
