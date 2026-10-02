import json
import zipfile
from datetime import date

import pytest

from app.data.goldencheetah import signed_metric
from app.data.activity_adapter import (
    activity_from_goldencheetah_ride,
    activities_from_goldencheetah_data,
    load_goldencheetah_activities,
)

def test_signed_metric_accepts_negative_value():
    result = signed_metric("-2.5")

    assert result == pytest.approx(-2.5)

def test_signed_metric_reads_metric_pair():
    result = signed_metric(["-2.5", "3600"])

    assert result == pytest.approx(-2.5)

def test_activity_from_goldencheetah_ride():
    ride = {
        "date": "2026/01/10 10:00:00 UTC",
        "sport": "Bike",
        "METRICS": {
            "workout_time": ["3600", "1"],
            "average_power": ["180", "3600"],
            "coggan_np": ["200", "3600"],
            "coggan_if": ["0.80", "3600"],
            "coggan_tss": ["64", "3600"],
            "aerobic_decoupling": ["-2.5", "1"],
        },
    }

    result = activity_from_goldencheetah_ride(
        ride
    )

    assert result is not None
    assert result.date == date(2026, 1, 10)
    assert result.duration_minutes == 60
    assert result.average_power == pytest.approx(180)
    assert result.normalized_power == pytest.approx(200)
    assert result.intensity_factor == pytest.approx(0.80)
    assert result.tss == pytest.approx(64)
    assert result.aerobic_decoupling == pytest.approx(-2.5)

def test_activity_adapter_ignores_non_cycling_activity():
    ride = {
        "date": "2026/01/10 10:00:00 UTC",
        "sport": "Run",
        "METRICS": {},
    }

    result = activity_from_goldencheetah_ride(
        ride
    )

    assert result is None

def test_activity_adapter_ignores_invalid_date():
    ride = {
        "date": "invalid",
        "sport": "Bike",
        "METRICS": {
            "workout_time": 3600,
            "average_power": 180,
            "coggan_np": 200,
        },
    }

    result = activity_from_goldencheetah_ride(
        ride
    )

    assert result is None

def test_activity_adapter_ignores_missing_required_metrics():
    ride = {
        "date": "2026/01/10 10:00:00 UTC",
        "sport": "Bike",
        "METRICS": {
            "workout_time": 3600,
            "average_power": 180,
        },
    }

    result = activity_from_goldencheetah_ride(
        ride
    )

    assert result is None

def test_activities_from_goldencheetah_data():
    valid_ride = {
        "date": "2026/01/10 10:00:00 UTC",
        "sport": "Bike",
        "METRICS": {
            "workout_time": 3600,
            "average_power": 180,
            "coggan_np": 200,
            "coggan_tss": 64,
            "aerobic_decoupling": 4.0,
        },
    }

    invalid_ride = {
        "date": "invalid",
        "sport": "Bike",
        "METRICS": {},
    }

    running_activity = {
        "date": "2026/01/11 10:00:00 UTC",
        "sport": "Run",
        "METRICS": {},
    }

    data = {
        "ATHLETE": {
            "id": "{athlete-a}",
        },
        "RIDES": [
            running_activity,
            invalid_ride,
            valid_ride,
        ],
    }

    activities, audit = (
        activities_from_goldencheetah_data(
            data
        )
    )

    assert len(activities) == 1
    assert activities[0].date == date(2026, 1, 10)

    assert audit == {
        "athlete_id": "athlete-a",
        "source_activities": 3,
        "imported_activities": 1,
        "skipped_non_bike": 1,
        "skipped_invalid": 1,
        "duplicate_activities": 0,
    }

def test_activities_are_sorted_by_date():
    data = {
        "ATHLETE": {
            "id": "{athlete-a}",
        },
        "RIDES": [
            {
                "date": ride_date,
                "sport": "Bike",
                "METRICS": {
                    "workout_time": 3600,
                    "average_power": 180,
                    "coggan_np": 200,
                    "coggan_tss": 64,
                },
            }
            for ride_date in [
                "2026/01/10 10:00:00 UTC",
                "2026/01/01 10:00:00 UTC",
            ]
        ],
    }

    activities, _ = (
        activities_from_goldencheetah_data(
            data
        )
    )

    assert [
        activity.date
        for activity in activities
    ] == [
        date(2026, 1, 1),
        date(2026, 1, 10),
    ]

def test_identical_duplicate_activity_is_ignored():
    ride = {
        "date": "2026/01/10 10:00:00 UTC",
        "sport": "Bike",
        "METRICS": {
            "workout_time": 3600,
            "average_power": 180,
            "coggan_np": 200,
            "coggan_tss": 64,
        },
    }

    data = {
        "ATHLETE": {
            "id": "{athlete-a}",
        },
        "RIDES": [
            ride,
            ride.copy(),
        ],
    }

    activities, audit = (
        activities_from_goldencheetah_data(
            data
        )
    )

    assert len(activities) == 1
    assert audit["duplicate_activities"] == 1

def test_multiple_activities_on_same_day_are_preserved():
    data = {
        "ATHLETE": {
            "id": "{athlete-a}",
        },
        "RIDES": [
            {
                "date": "2026/01/10 10:00:00 UTC",
                "sport": "Bike",
                "METRICS": {
                    "workout_time": 3600,
                    "average_power": 180,
                    "coggan_np": 200,
                    "coggan_tss": 64,
                },
            },
            {
                "date": "2026/01/10 18:00:00 UTC",
                "sport": "Bike",
                "METRICS": {
                    "workout_time": 1800,
                    "average_power": 150,
                    "coggan_np": 170,
                    "coggan_tss": 30,
                },
            },
        ],
    }

    activities, audit = (
        activities_from_goldencheetah_data(
            data
        )
    )

    assert len(activities) == 2
    assert audit["duplicate_activities"] == 0

def test_conflicting_activities_at_same_datetime_raise_error():
    data = {
        "ATHLETE": {
            "id": "{athlete-a}",
        },
        "RIDES": [
            {
                "date": "2026/01/10 10:00:00 UTC",
                "sport": "Bike",
                "METRICS": {
                    "workout_time": 3600,
                    "average_power": 180,
                    "coggan_np": 200,
                    "coggan_tss": 64,
                },
            },
            {
                "date": "2026/01/10 10:00:00 UTC",
                "sport": "Bike",
                "METRICS": {
                    "workout_time": 5400,
                    "average_power": 190,
                    "coggan_np": 210,
                    "coggan_tss": 80,
                },
            },
        ],
    }

    with pytest.raises(ValueError):
        activities_from_goldencheetah_data(
            data
        )

def test_load_goldencheetah_activities_from_json(
    tmp_path,
):
    path = tmp_path / "athlete.json"

    data = {
        "ATHLETE": {
            "id": "{athlete-a}",
        },
        "RIDES": [
            {
                "date": "2026/01/10 10:00:00 UTC",
                "sport": "Bike",
                "METRICS": {
                    "workout_time": 3600,
                    "average_power": 180,
                    "coggan_np": 200,
                    "coggan_tss": 64,
                    "aerobic_decoupling": 4.0,
                },
            },
        ],
    }

    path.write_text(
        json.dumps(data),
        encoding="utf-8",
    )

    activities, audit = (
        load_goldencheetah_activities(path)
    )

    assert len(activities) == 1
    assert audit["athlete_id"] == "athlete-a"
    assert audit["source"] == str(path)

def test_load_goldencheetah_activities_from_zip(
    tmp_path,
):
    path = tmp_path / "athlete.zip"

    data = {
        "ATHLETE": {
            "id": "{athlete-a}",
        },
        "RIDES": [
            {
                "date": "2026/01/10 10:00:00 UTC",
                "sport": "Bike",
                "METRICS": {
                    "workout_time": 3600,
                    "average_power": 180,
                    "coggan_np": 200,
                    "coggan_tss": 64,
                    "aerobic_decoupling": 4.0,
                },
            },
        ],
    }

    with zipfile.ZipFile(path, "w") as archive:
        archive.writestr(
            "athlete.json",
            json.dumps(data),
        )

    activities, audit = (
        load_goldencheetah_activities(path)
    )

    assert len(activities) == 1
    assert activities[0].date == date(2026, 1, 10)
    assert audit["athlete_id"] == "athlete-a"
    assert audit["imported_activities"] == 1
