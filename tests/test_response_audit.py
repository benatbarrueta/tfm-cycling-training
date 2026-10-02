import pytest
import csv
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
    extract_longest_continuous_paired_segment,
    split_segment_by_time,
    calculate_aerobic_decoupling,
    build_activity_response,
    build_decoupling_comparison,
    collect_athlete_decoupling_comparisons,
    save_decoupling_comparisons,
    summarize_decoupling_halves,
    summarize_segment_stability,
    is_eligible_decoupling_response,
    filter_eligible_decoupling_comparisons,
    build_response_session_features,
    summarize_prior_load,
    build_response_history_features,
    has_prior_history_span,
    build_response_dataset_row,
    summarize_prior_responses,
    build_athlete_response_rows,
    save_response_dataset,
    build_relative_load_features,
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

def test_collect_athlete_decoupling_comparisons(tmp_path):
    zip_path = tmp_path / "athlete.zip"

    summary = {
        "ATHLETE": {
            "id": "{athlete-a}",
        },
        "RIDES": [
            {
                "date": "2026/01/01 10:00:00 UTC",
                "sport": "Bike",
                "METRICS": {
                    "average_power": 190,
                    "average_hr": 100,
                    "aerobic_decoupling": 8,
                },
            },
        ],
    }

    csv_content = "secs,power,hr\n" + "".join(
        (
            f"{second},"
            f"{200 if second <= 600 else 180},"
            "100\n"
        )
        for second in range(0, 1201)
    )

    with zipfile.ZipFile(zip_path, "w") as archive:
        archive.writestr(
            "athlete.json",
            json.dumps(summary),
        )
        archive.writestr(
            "2026_01_01_10_00_00.csv",
            csv_content,
        )

    result = collect_athlete_decoupling_comparisons(
        zip_path
    )

    expected_mean_power = (
        601 * 200 + 600 * 180
    ) / 1201

    expected_power_variance = (
        601 * (200 - expected_mean_power) ** 2
        + 600 * (180 - expected_mean_power) ** 2
    ) / 1201

    expected_power_standard_deviation = (
        expected_power_variance ** 0.5
    )

    assert len(result) == 1

    assert result[0] == {
        "athlete_id": "athlete-a",
        "csv_name": "2026_01_01_10_00_00.csv",
        "ride_date": "2026/01/01 10:00:00 UTC",
        "reported_decoupling": 8.0,
        "calculated_decoupling": pytest.approx(10.0),
        "difference": pytest.approx(2.0),
        "continuous_duration_seconds": 1200,
        "paired_sample_count": 1201,
        "first_half_power": pytest.approx(200.0),
        "second_half_power": pytest.approx(180.0),
        "first_half_hr": pytest.approx(100.0),
        "second_half_hr": pytest.approx(100.0),
        "first_half_ratio": pytest.approx(2.0),
        "second_half_ratio": pytest.approx(1.8),
        "mean_power": pytest.approx(
            expected_mean_power
        ),
        "power_standard_deviation": pytest.approx(
            expected_power_standard_deviation
        ),
        "power_cv": pytest.approx(
            expected_power_standard_deviation
            / expected_mean_power
        ),
        "zero_power_fraction": pytest.approx(0.0),
        "power_balance_ratio": pytest.approx(0.9),
    }

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

def test_extract_longest_continuous_paired_segment():
    samples = [
        {"secs": "0", "power": "200", "hr": "140"},
        {"secs": "1", "power": "210", "hr": "141"},
        {"secs": "2", "power": "", "hr": "142"},
        {"secs": "4", "power": "220", "hr": "143"},
        {"secs": "10", "power": "230", "hr": "144"},
        {"secs": "11", "power": "240", "hr": "145"},
    ]

    result = extract_longest_continuous_paired_segment(
        samples,
        max_gap_seconds=5,
    )

    assert result == [
        {"secs": "0", "power": "200", "hr": "140"},
        {"secs": "1", "power": "210", "hr": "141"},
        {"secs": "4", "power": "220", "hr": "143"},
    ]

def test_extract_longest_continuous_paired_segment_empty():
    assert extract_longest_continuous_paired_segment([]) == []

def test_extract_longest_continuous_paired_segment_rejects_invalid_gap():
    with pytest.raises(ValueError):
        extract_longest_continuous_paired_segment(
            [],
            max_gap_seconds=0,
        )

def test_split_segment_by_time():
    segment = [
        {"secs": "0", "power": "200", "hr": "140"},
        {"secs": "1", "power": "210", "hr": "141"},
        {"secs": "4", "power": "220", "hr": "143"},
        {"secs": "5", "power": "225", "hr": "144"},
        {"secs": "8", "power": "230", "hr": "145"},
    ]

    first_half, second_half = split_segment_by_time(segment)

    assert first_half == segment[:3]
    assert second_half == segment[3:]

def test_split_segment_by_time_requires_two_samples():
    with pytest.raises(ValueError):
        split_segment_by_time([
            {"secs": "0", "power": "200", "hr": "140"},
        ])

def test_split_segment_by_time_requires_increasing_time():
    segment = [
        {"secs": "10", "power": "200", "hr": "140"},
        {"secs": "10", "power": "210", "hr": "141"},
    ]

    with pytest.raises(ValueError):
        split_segment_by_time(segment)

def test_calculate_aerobic_decoupling():
    segment = [
        {"secs": "0", "power": "200", "hr": "100"},
        {"secs": "1", "power": "200", "hr": "100"},
        {"secs": "2", "power": "180", "hr": "100"},
        {"secs": "3", "power": "180", "hr": "100"},
    ]

    result = calculate_aerobic_decoupling(segment)

    assert result == pytest.approx(10.0)

def test_calculate_aerobic_decoupling_without_change():
    segment = [
        {"secs": "0", "power": "200", "hr": "100"},
        {"secs": "1", "power": "200", "hr": "100"},
        {"secs": "2", "power": "220", "hr": "110"},
        {"secs": "3", "power": "220", "hr": "110"},
    ]

    result = calculate_aerobic_decoupling(segment)

    assert result == pytest.approx(0.0)

def test_calculate_aerobic_decoupling_with_zero_power():
    segment = [
        {"secs": "0", "power": "0", "hr": "100"},
        {"secs": "1", "power": "0", "hr": "100"},
        {"secs": "2", "power": "180", "hr": "100"},
        {"secs": "3", "power": "180", "hr": "100"},
    ]

    assert calculate_aerobic_decoupling(segment) is None

def test_build_activity_response():
    samples = [
        {"secs": "0", "power": "200", "hr": "100"},
        {"secs": "1", "power": "200", "hr": "100"},
        {"secs": "2", "power": "180", "hr": "100"},
        {"secs": "3", "power": "180", "hr": "100"},
    ]

    result = build_activity_response(
        samples,
        min_duration_seconds=3,
    )

    assert result == {
        "continuous_duration_seconds": 3,
        "paired_sample_count": 4,
        "first_half_power": pytest.approx(200.0),
        "second_half_power": pytest.approx(180.0),
        "first_half_hr": pytest.approx(100.0),
        "second_half_hr": pytest.approx(100.0),
        "first_half_ratio": pytest.approx(2.0),
        "second_half_ratio": pytest.approx(1.8),
        "mean_power": pytest.approx(190.0),
        "power_standard_deviation": pytest.approx(10.0),
        "power_cv": pytest.approx(10 / 190),
        "zero_power_fraction": pytest.approx(0.0),
        "power_balance_ratio": pytest.approx(0.9),
        "aerobic_decoupling": pytest.approx(10.0),
    }

def test_build_activity_response_rejects_short_segment():
    samples = [
        {"secs": "0", "power": "200", "hr": "100"},
        {"secs": "1", "power": "200", "hr": "100"},
    ]

    result = build_activity_response(
        samples,
        min_duration_seconds=20 * 60,
    )

    assert result is None

def test_build_activity_response_rejects_invalid_duration():
    with pytest.raises(ValueError):
        build_activity_response(
            [],
            min_duration_seconds=0,
        )

def test_build_decoupling_comparison():
    ride = {
        "date": "2026/01/01 10:00:00 UTC",
        "METRICS": {
            "aerobic_decoupling": ["8", "1"],
        },
    }

    samples = [
        {"secs": "0", "power": "200", "hr": "100"},
        {"secs": "1", "power": "200", "hr": "100"},
        {"secs": "2", "power": "180", "hr": "100"},
        {"secs": "3", "power": "180", "hr": "100"},
    ]

    result = build_decoupling_comparison(
        ride,
        samples,
        min_duration_seconds=3,
    )

    assert result == {
        "ride_date": "2026/01/01 10:00:00 UTC",
        "reported_decoupling": 8.0,
        "calculated_decoupling": pytest.approx(10.0),
        "difference": pytest.approx(2.0),
        "continuous_duration_seconds": 3,
        "paired_sample_count": 4,
        "first_half_power": pytest.approx(200.0),
        "second_half_power": pytest.approx(180.0),
        "first_half_hr": pytest.approx(100.0),
        "second_half_hr": pytest.approx(100.0),
        "first_half_ratio": pytest.approx(2.0),
        "second_half_ratio": pytest.approx(1.8),
        "mean_power": pytest.approx(190.0),
        "power_standard_deviation": pytest.approx(10.0),
        "power_cv": pytest.approx(10 / 190),
        "zero_power_fraction": pytest.approx(0.0),
        "power_balance_ratio": pytest.approx(0.9),
    }

def test_build_decoupling_comparison_without_reported_value():
    ride = {
        "date": "2026/01/01 10:00:00 UTC",
        "METRICS": {},
    }

    assert build_decoupling_comparison(
        ride,
        [],
    ) is None

def test_build_decoupling_comparison_rejects_short_activity():
    ride = {
        "date": "2026/01/01 10:00:00 UTC",
        "METRICS": {
            "aerobic_decoupling": 8,
        },
    }

    samples = [
        {"secs": "0", "power": "200", "hr": "100"},
        {"secs": "1", "power": "180", "hr": "100"},
    ]

    assert build_decoupling_comparison(
        ride,
        samples,
        min_duration_seconds=20 * 60,
    ) is None

def test_save_decoupling_comparisons(tmp_path):
    output = tmp_path / "results" / "decoupling.csv"

    comparisons = [
        {
            "athlete_id": "athlete-a",
            "csv_name": "activity.csv",
            "ride_date": "2026/01/01 10:00:00 UTC",
            "reported_decoupling": 8.0,
            "calculated_decoupling": 10.0,
            "difference": 2.0,
            "continuous_duration_seconds": 1200,
            "paired_sample_count": 1201,
            "first_half_power": 200.0,
            "second_half_power": 180.0,
            "first_half_hr": 100.0,
            "second_half_hr": 100.0,
            "first_half_ratio": 2.0,
            "second_half_ratio": 1.8,
            "mean_power": 190.0,
            "power_standard_deviation": 10.0,
            "power_cv": 10 / 190,
            "zero_power_fraction": 0.0,
            "power_balance_ratio": 0.9,
        },
    ]

    save_decoupling_comparisons(
        comparisons,
        output,
    )

    with output.open(
        encoding="utf-8",
        newline="",
    ) as file:
        rows = list(csv.DictReader(file))

    assert rows == [
        {
            "athlete_id": "athlete-a",
            "csv_name": "activity.csv",
            "ride_date": "2026/01/01 10:00:00 UTC",
            "reported_decoupling": "8.0",
            "calculated_decoupling": "10.0",
            "difference": "2.0",
            "continuous_duration_seconds": "1200",
            "paired_sample_count": "1201",
            "first_half_power": "200.0",
            "second_half_power": "180.0",
            "first_half_hr": "100.0",
            "second_half_hr": "100.0",
            "first_half_ratio": "2.0",
            "second_half_ratio": "1.8",
            "mean_power": "190.0",
            "power_standard_deviation": "10.0",
            "power_cv": str(10 / 190),
            "zero_power_fraction": "0.0",
            "power_balance_ratio": "0.9",
        },
    ]

def test_save_decoupling_comparisons_rejects_empty_list(
    tmp_path,
):
    output = tmp_path / "decoupling.csv"

    with pytest.raises(ValueError):
        save_decoupling_comparisons(
            [],
            output,
        )

def test_summarize_decoupling_halves():
    segment = [
        {"secs": "0", "power": "200", "hr": "100"},
        {"secs": "1", "power": "200", "hr": "100"},
        {"secs": "2", "power": "180", "hr": "100"},
        {"secs": "3", "power": "180", "hr": "100"},
    ]

    result = summarize_decoupling_halves(segment)

    assert result == {
        "first_half_power": pytest.approx(200.0),
        "second_half_power": pytest.approx(180.0),
        "first_half_hr": pytest.approx(100.0),
        "second_half_hr": pytest.approx(100.0),
        "first_half_ratio": pytest.approx(2.0),
        "second_half_ratio": pytest.approx(1.8),
    }

def test_summarize_segment_stability():
    segment = [
        {"secs": "0", "power": "200", "hr": "100"},
        {"secs": "1", "power": "200", "hr": "100"},
        {"secs": "2", "power": "180", "hr": "100"},
        {"secs": "3", "power": "180", "hr": "100"},
    ]

    result = summarize_segment_stability(segment)

    assert result == {
        "mean_power": pytest.approx(190.0),
        "power_standard_deviation": pytest.approx(10.0),
        "power_cv": pytest.approx(10 / 190),
        "zero_power_fraction": pytest.approx(0.0),
        "power_balance_ratio": pytest.approx(0.9),
    }

def test_summarize_segment_stability_empty():
    with pytest.raises(ValueError):
        summarize_segment_stability([])

def test_is_eligible_decoupling_response():
    response = {
        "power_cv": 0.50,
        "zero_power_fraction": 0.10,
        "power_balance_ratio": 0.90,
    }

    assert is_eligible_decoupling_response(response)

@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("power_cv", 0.76),
        ("zero_power_fraction", 0.21),
        ("power_balance_ratio", 0.79),
    ],
)
def test_is_eligible_decoupling_response_rejects_unstable_activity(
    field,
    value,
):
    response = {
        "power_cv": 0.50,
        "zero_power_fraction": 0.10,
        "power_balance_ratio": 0.90,
    }
    response[field] = value

    assert not is_eligible_decoupling_response(response)

def test_is_eligible_decoupling_response_validates_thresholds():
    response = {
        "power_cv": 0.50,
        "zero_power_fraction": 0.10,
        "power_balance_ratio": 0.90,
    }

    with pytest.raises(ValueError):
        is_eligible_decoupling_response(
            response,
            max_power_cv=-0.1,
        )

    with pytest.raises(ValueError):
        is_eligible_decoupling_response(
            response,
            max_zero_power_fraction=1.1,
        )

    with pytest.raises(ValueError):
        is_eligible_decoupling_response(
            response,
            min_power_balance_ratio=-0.1,
        )

def test_filter_eligible_decoupling_comparisons():
    eligible = {
        "ride_date": "2026/01/01 10:00:00 UTC",
        "power_cv": 0.50,
        "zero_power_fraction": 0.10,
        "power_balance_ratio": 0.90,
    }

    rejected = {
        "ride_date": "2026/01/02 10:00:00 UTC",
        "power_cv": 0.90,
        "zero_power_fraction": 0.10,
        "power_balance_ratio": 0.90,
    }

    result = filter_eligible_decoupling_comparisons([
        eligible,
        rejected,
    ])

    assert result == [eligible]

def test_filter_eligible_decoupling_comparisons_empty():
    assert filter_eligible_decoupling_comparisons([]) == []

def test_build_response_session_features():
    ride = {
        "METRICS": {
            "workout_time": "3600",
            "coggan_if": ["0.75", "3600"],
            "coggan_tss": "56.25",
        },
    }

    result = build_response_session_features(ride)

    assert result == {
        "session_duration_minutes": pytest.approx(60.0),
        "session_intensity_factor": pytest.approx(0.75),
        "session_tss": pytest.approx(56.25),
    }

@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("workout_time", ""),
        ("workout_time", "0"),
        ("coggan_if", ""),
        ("coggan_if", "0"),
        ("coggan_tss", ""),
        ("coggan_tss", "-1"),
    ],
)
def test_build_response_session_features_rejects_invalid_metrics(
    field,
    value,
):
    metrics = {
        "workout_time": "3600",
        "coggan_if": "0.75",
        "coggan_tss": "56.25",
    }
    metrics[field] = value

    assert build_response_session_features({
        "METRICS": metrics,
    }) is None

def test_summarize_prior_load():
    rides = [
        {
            "date": "2026/01/03 10:00:00 UTC",
            "sport": "Bike",
            "METRICS": {"coggan_tss": "50"},
        },
        {
            "date": "2026/01/08 10:00:00 UTC",
            "sport": "Bike",
            "METRICS": {"coggan_tss": "70"},
        },
        {
            "date": "2026/01/09 10:00:00 UTC",
            "sport": "Bike",
            "METRICS": {},
        },
        {
            "date": "2026/01/09 12:00:00 UTC",
            "sport": "Run",
            "METRICS": {"coggan_tss": "100"},
        },
        {
            "date": "2026/01/11 10:00:00 UTC",
            "sport": "Bike",
            "METRICS": {"coggan_tss": "200"},
        },
    ]

    result = summarize_prior_load(
        rides,
        "2026/01/10 10:00:00 UTC",
        days=7,
    )

    assert result == {
        "observed_tss": pytest.approx(120.0),
        "activity_count": 3,
        "tss_coverage": pytest.approx(2 / 3),
    }

def test_summarize_prior_load_without_activities():
    result = summarize_prior_load(
        [],
        "2026/01/10 10:00:00 UTC",
        days=7,
    )

    assert result == {
        "observed_tss": 0,
        "activity_count": 0,
        "tss_coverage": 1.0,
    }

def test_summarize_prior_load_rejects_invalid_days():
    with pytest.raises(ValueError):
        summarize_prior_load(
            [],
            "2026/01/10 10:00:00 UTC",
            days=0,
        )

def test_build_response_history_features():
    rides = [
        {
            "date": "2025/12/20 10:00:00 UTC",
            "sport": "Bike",
            "METRICS": {"coggan_tss": "40"},
        },
        {
            "date": "2026/01/05 10:00:00 UTC",
            "sport": "Bike",
            "METRICS": {"coggan_tss": "50"},
        },
        {
            "date": "2026/01/08 10:00:00 UTC",
            "sport": "Bike",
            "METRICS": {"coggan_tss": "70"},
        },
        {
            "date": "2026/01/09 10:00:00 UTC",
            "sport": "Bike",
            "METRICS": {},
        },
    ]

    result = build_response_history_features(
        rides,
        "2026/01/10 10:00:00 UTC",
    )

    assert result == {
        "previous_7d_tss": pytest.approx(120.0),
        "previous_7d_activity_count": 3,
        "previous_7d_tss_coverage": pytest.approx(2 / 3),
        "previous_28d_tss": pytest.approx(160.0),
        "previous_28d_activity_count": 4,
        "previous_28d_tss_coverage": pytest.approx(3 / 4),
    }

def test_build_response_history_excludes_target_activity():
    rides = [
        {
            "date": "2026/01/10 10:00:00 UTC",
            "sport": "Bike",
            "METRICS": {"coggan_tss": "100"},
        },
    ]

    result = build_response_history_features(
        rides,
        "2026/01/10 10:00:00 UTC",
    )

    assert result["previous_7d_tss"] == 0
    assert result["previous_28d_tss"] == 0

def test_has_prior_history_span():
    rides = [
        {
            "date": "2025/12/01 10:00:00 UTC",
            "sport": "Bike",
        },
        {
            "date": "2026/01/05 10:00:00 UTC",
            "sport": "Bike",
        },
    ]

    assert has_prior_history_span(
        rides,
        "2026/01/10 10:00:00 UTC",
        days=28,
    )

def test_has_prior_history_span_rejects_short_history():
    rides = [
        {
            "date": "2026/01/05 10:00:00 UTC",
            "sport": "Bike",
        },
    ]

    assert not has_prior_history_span(
        rides,
        "2026/01/10 10:00:00 UTC",
        days=28,
    )

def test_has_prior_history_span_ignores_future_rides():
    rides = [
        {
            "date": "2026/02/01 10:00:00 UTC",
            "sport": "Bike",
        },
    ]

    assert not has_prior_history_span(
        rides,
        "2026/01/10 10:00:00 UTC",
        days=28,
    )

def test_has_prior_history_span_rejects_invalid_days():
    with pytest.raises(ValueError):
        has_prior_history_span(
            [],
            "2026/01/10 10:00:00 UTC",
            days=0,
        )

def test_build_response_dataset_row():
    historical_ride = {
        "date": "2025/12/01 10:00:00 UTC",
        "sport": "Bike",
        "METRICS": {
            "coggan_tss": "40",
        },
    }

    recent_ride = {
        "date": "2026/01/05 10:00:00 UTC",
        "sport": "Bike",
        "METRICS": {
            "coggan_tss": "50",
        },
    }

    target_ride = {
        "date": "2026/01/10 10:00:00 UTC",
        "sport": "Bike",
        "METRICS": {
            "workout_time": "3600",
            "coggan_if": "0.75",
            "coggan_tss": "56.25",
        },
    }

    rides = [
        historical_ride,
        recent_ride,
        target_ride,
    ]

    comparison = {
        "reported_decoupling": 8.0,
        "power_cv": 0.50,
        "zero_power_fraction": 0.10,
        "power_balance_ratio": 0.90,
    }

    result = build_response_dataset_row(
        "athlete-a",
        rides,
        target_ride,
        comparison,
    )

    assert result == {
        "athlete_id": "athlete-a",
        "activity_date": "2026/01/10 10:00:00 UTC",
        "session_duration_minutes": pytest.approx(60.0),
        "session_intensity_factor": pytest.approx(0.75),
        "session_tss": pytest.approx(56.25),
        "previous_7d_tss": pytest.approx(50.0),
        "previous_7d_activity_count": 1,
        "previous_7d_tss_coverage": pytest.approx(1.0),
        "previous_28d_tss": pytest.approx(50.0),
        "previous_28d_activity_count": 1,
        "previous_28d_tss_coverage": pytest.approx(1.0),
        "target_aerobic_decoupling": pytest.approx(8.0),
        "acute_chronic_load_ratio": pytest.approx(4.0),
        "session_to_chronic_load_ratio": pytest.approx(4.5),
    }

def test_build_response_dataset_row_rejects_zero_chronic_load():
    old_ride = {
        "date": "2025/12/01 10:00:00 UTC",
        "sport": "Bike",
        "METRICS": {
            "coggan_tss": "0",
        },
    }

    target_ride = {
        "date": "2026/01/10 10:00:00 UTC",
        "sport": "Bike",
        "METRICS": {
            "workout_time": "3600",
            "coggan_if": "0.75",
            "coggan_tss": "56.25",
        },
    }

    comparison = {
        "reported_decoupling": 8.0,
        "power_cv": 0.50,
        "zero_power_fraction": 0.10,
        "power_balance_ratio": 0.90,
    }

    assert build_response_dataset_row(
        "athlete-a",
        [
            old_ride,
            target_ride,
        ],
        target_ride,
        comparison,
    ) is None

def test_build_response_dataset_row_rejects_incomplete_history():
    old_ride = {
        "date": "2025/12/01 10:00:00 UTC",
        "sport": "Bike",
        "METRICS": {
            "coggan_tss": "40",
        },
    }

    incomplete_ride = {
        "date": "2026/01/05 10:00:00 UTC",
        "sport": "Bike",
        "METRICS": {},
    }

    target_ride = {
        "date": "2026/01/10 10:00:00 UTC",
        "sport": "Bike",
        "METRICS": {
            "workout_time": "3600",
            "coggan_if": "0.75",
            "coggan_tss": "56.25",
        },
    }

    comparison = {
        "reported_decoupling": 8.0,
        "power_cv": 0.50,
        "zero_power_fraction": 0.10,
        "power_balance_ratio": 0.90,
    }

    assert build_response_dataset_row(
        "athlete-a",
        [
            old_ride,
            incomplete_ride,
            target_ride,
        ],
        target_ride,
        comparison,
    ) is None

def test_build_response_dataset_row_rejects_ineligible_response():
    ride = {
        "date": "2026/01/10 10:00:00 UTC",
        "sport": "Bike",
        "METRICS": {},
    }

    comparison = {
        "reported_decoupling": 8.0,
        "power_cv": 0.90,
        "zero_power_fraction": 0.10,
        "power_balance_ratio": 0.90,
    }

    assert build_response_dataset_row(
        "athlete-a",
        [],
        ride,
        comparison,
    ) is None

def test_build_response_dataset_row_rejects_short_history():
    ride = {
        "date": "2026/01/10 10:00:00 UTC",
        "sport": "Bike",
        "METRICS": {
            "workout_time": "3600",
            "coggan_if": "0.75",
            "coggan_tss": "56.25",
        },
    }

    comparison = {
        "reported_decoupling": 8.0,
        "power_cv": 0.50,
        "zero_power_fraction": 0.10,
        "power_balance_ratio": 0.90,
    }

    assert build_response_dataset_row(
        "athlete-a",
        [ride],
        ride,
        comparison,
    ) is None

def test_summarize_prior_responses():
    comparisons = [
        {
            "ride_date": "2026/01/01 10:00:00 UTC",
            "reported_decoupling": 4.0,
            "power_cv": 0.50,
            "zero_power_fraction": 0.10,
            "power_balance_ratio": 0.90,
        },
        {
            "ride_date": "2026/01/03 10:00:00 UTC",
            "reported_decoupling": 8.0,
            "power_cv": 0.50,
            "zero_power_fraction": 0.10,
            "power_balance_ratio": 0.90,
        },
        {
            "ride_date": "2026/01/05 10:00:00 UTC",
            "reported_decoupling": 12.0,
            "power_cv": 0.50,
            "zero_power_fraction": 0.10,
            "power_balance_ratio": 0.90,
        },
        {
            "ride_date": "2026/01/06 10:00:00 UTC",
            "reported_decoupling": 50.0,
            "power_cv": 0.90,
            "zero_power_fraction": 0.10,
            "power_balance_ratio": 0.90,
        },
        {
            "ride_date": "2026/01/20 10:00:00 UTC",
            "reported_decoupling": 100.0,
            "power_cv": 0.50,
            "zero_power_fraction": 0.10,
            "power_balance_ratio": 0.90,
        },
    ]

    result = summarize_prior_responses(
        comparisons,
        "2026/01/10 10:00:00 UTC",
    )

    assert result == {
        "previous_response_median": pytest.approx(8.0),
        "previous_response_count": 3,
    }

def test_summarize_prior_responses_requires_three_values():
    comparisons = [
        {
            "ride_date": "2026/01/01 10:00:00 UTC",
            "reported_decoupling": 4.0,
            "power_cv": 0.50,
            "zero_power_fraction": 0.10,
            "power_balance_ratio": 0.90,
        },
        {
            "ride_date": "2026/01/03 10:00:00 UTC",
            "reported_decoupling": 8.0,
            "power_cv": 0.50,
            "zero_power_fraction": 0.10,
            "power_balance_ratio": 0.90,
        },
    ]

    assert summarize_prior_responses(
        comparisons,
        "2026/01/10 10:00:00 UTC",
    ) is None

def test_build_athlete_response_rows():
    historical_ride = {
        "date": "2025/12/01 10:00:00 UTC",
        "sport": "Bike",
        "METRICS": {
            "coggan_tss": "40",
        },
    }

    recent_ride = {
        "date": "2026/01/05 10:00:00 UTC",
        "sport": "Bike",
        "METRICS": {
            "coggan_tss": "50",
        },
    }

    target_ride = {
        "date": "2026/01/10 10:00:00 UTC",
        "sport": "Bike",
        "METRICS": {
            "workout_time": "3600",
            "coggan_if": "0.75",
            "coggan_tss": "56.25",
        },
    }

    data = {
        "ATHLETE": {
            "id": "{athlete-a}",
        },
        "RIDES": [
            historical_ride,
            recent_ride,
            target_ride,
        ],
    }

    comparisons = [
        {
            "ride_date": "2026/01/01 10:00:00 UTC",
            "reported_decoupling": 4.0,
            "power_cv": 0.50,
            "zero_power_fraction": 0.10,
            "power_balance_ratio": 0.90,
        },
        {
            "ride_date": "2026/01/03 10:00:00 UTC",
            "reported_decoupling": 8.0,
            "power_cv": 0.50,
            "zero_power_fraction": 0.10,
            "power_balance_ratio": 0.90,
        },
        {
            "ride_date": "2026/01/05 09:00:00 UTC",
            "reported_decoupling": 12.0,
            "power_cv": 0.50,
            "zero_power_fraction": 0.10,
            "power_balance_ratio": 0.90,
        },
        {
            "ride_date": "2026/01/10 10:00:00 UTC",
            "reported_decoupling": 8.0,
            "power_cv": 0.50,
            "zero_power_fraction": 0.10,
            "power_balance_ratio": 0.90,
        },
    ]

    result = build_athlete_response_rows(
        data,
        comparisons,
    )

    assert len(result) == 1
    assert result[0]["athlete_id"] == "athlete-a"
    assert result[0]["activity_date"] == (
        "2026/01/10 10:00:00 UTC"
    )
    assert result[0]["target_aerobic_decoupling"] == (
        pytest.approx(8.0)
    )
    assert result[0]["previous_7d_tss"] == pytest.approx(50.0)
    assert result[0]["previous_response_median"] == (
        pytest.approx(8.0)
    )
    assert result[0]["previous_response_count"] == 3

def test_build_athlete_response_rows_skips_duplicate_dates():
    duplicate_ride = {
        "date": "2026/01/10 10:00:00 UTC",
        "sport": "Bike",
        "METRICS": {},
    }

    data = {
        "ATHLETE": {"id": "{athlete-a}"},
        "RIDES": [
            duplicate_ride,
            duplicate_ride.copy(),
        ],
    }

    comparisons = [
        {
            "ride_date": "2026/01/10 10:00:00 UTC",
            "reported_decoupling": 8.0,
            "power_cv": 0.50,
            "zero_power_fraction": 0.10,
            "power_balance_ratio": 0.90,
        },
    ]

    assert build_athlete_response_rows(
        data,
        comparisons,
    ) == []

def test_save_response_dataset(tmp_path):
    output = tmp_path / "response_dataset.csv"

    rows = [
        {
            "athlete_id": "athlete-a",
            "activity_date": "2026/01/10 10:00:00 UTC",
            "session_duration_minutes": 60.0,
            "session_intensity_factor": 0.75,
            "session_tss": 56.25,
            "previous_7d_tss": 50.0,
            "previous_7d_activity_count": 1,
            "previous_7d_tss_coverage": 1.0,
            "previous_28d_tss": 150.0,
            "previous_28d_activity_count": 3,
            "previous_28d_tss_coverage": 1.0,
            "acute_chronic_load_ratio": 1.25,
            "session_to_chronic_load_ratio": 0.25,
            "target_aerobic_decoupling": 8.0,
            "previous_response_median": 7.0,
            "previous_response_count": 3,
        },
    ]

    save_response_dataset(
        rows,
        output,
    )

    with output.open(
        encoding="utf-8",
        newline="",
    ) as file:
        saved_rows = list(csv.DictReader(file))

    assert saved_rows == [
        {
            "athlete_id": "athlete-a",
            "activity_date": "2026/01/10 10:00:00 UTC",
            "session_duration_minutes": "60.0",
            "session_intensity_factor": "0.75",
            "session_tss": "56.25",
            "previous_7d_tss": "50.0",
            "previous_7d_activity_count": "1",
            "previous_7d_tss_coverage": "1.0",
            "previous_28d_tss": "150.0",
            "previous_28d_activity_count": "3",
            "previous_28d_tss_coverage": "1.0",
            "acute_chronic_load_ratio": "1.25",
            "session_to_chronic_load_ratio": "0.25",
            "target_aerobic_decoupling": "8.0",
            "previous_response_median": "7.0",
            "previous_response_count": "3",
        },
    ]

def test_save_response_dataset_rejects_empty_rows(
    tmp_path,
):
    with pytest.raises(ValueError):
        save_response_dataset(
            [],
            tmp_path / "response_dataset.csv",
        )

def test_build_relative_load_features():
    history_features = {
        "previous_7d_tss": 500,
        "previous_28d_tss": 1600,
    }

    result = build_relative_load_features(
        100,
        history_features,
    )

    assert result == {
        "acute_chronic_load_ratio": pytest.approx(1.25),
        "session_to_chronic_load_ratio": pytest.approx(0.25),
    }

def test_build_relative_load_features_requires_chronic_load():
    history_features = {
        "previous_7d_tss": 0,
        "previous_28d_tss": 0,
    }

    assert build_relative_load_features(
        50,
        history_features,
    ) is None