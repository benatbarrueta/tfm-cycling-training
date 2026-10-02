import pytest

from datetime import date

from app.models.activity import Activity
from app.models.aerobic_response import AerobicResponse

from app.services.aerobic_response_service import (
    classify_aerobic_response,
    estimate_personal_decoupling,
    estimate_aerobic_response_from_activities,
)


def test_estimate_personal_decoupling():
    result = estimate_personal_decoupling(
        [4.0, 8.0, 6.0, 5.0]
    )

    assert result == pytest.approx(5.5)

def test_estimate_personal_decoupling_with_insufficient_history():
    result = estimate_personal_decoupling(
        [4.0, 6.0]
    )

    assert result is None

def test_estimate_personal_decoupling_rejects_non_finite_values():
    with pytest.raises(ValueError):
        estimate_personal_decoupling(
            [4.0, float("nan"), 6.0]
        )

def test_classify_unknown_aerobic_response():
    result = classify_aerobic_response(None)

    assert result == AerobicResponse.UNKNOWN

def test_classify_stable_aerobic_response():
    result = classify_aerobic_response(5.0)

    assert result == AerobicResponse.STABLE

def test_classify_elevated_aerobic_response():
    result = classify_aerobic_response(5.01)

    assert result == AerobicResponse.ELEVATED

def test_classify_aerobic_response_accepts_negative_values():
    result = classify_aerobic_response(-2.0)

    assert result == AerobicResponse.STABLE

def test_estimate_stable_response_from_activities():
    activities = [
        Activity(
            date=date(2026, 1, day),
            duration_minutes=60,
            average_power=180,
            normalized_power=200,
            aerobic_decoupling=decoupling,
        )
        for day, decoupling in [
            (1, 3.0),
            (2, 4.0),
            (3, 5.0),
        ]
    ]

    result = estimate_aerobic_response_from_activities(
        activities,
        reference_date=date(2026, 1, 10),
    )

    assert result == AerobicResponse.STABLE

def test_estimate_elevated_response_from_activities():
    activities = [
        Activity(
            date=date(2026, 1, day),
            duration_minutes=60,
            average_power=180,
            normalized_power=200,
            aerobic_decoupling=decoupling,
        )
        for day, decoupling in [
            (1, 6.0),
            (2, 8.0),
            (3, 7.0),
        ]
    ]

    result = estimate_aerobic_response_from_activities(
        activities,
        reference_date=date(2026, 1, 10),
    )

    assert result == AerobicResponse.ELEVATED

def test_estimate_unknown_response_with_insufficient_activities():
    activities = [
        Activity(
            date=date(2026, 1, 1),
            duration_minutes=60,
            average_power=180,
            normalized_power=200,
            aerobic_decoupling=4.0,
        ),
        Activity(
            date=date(2026, 1, 2),
            duration_minutes=60,
            average_power=180,
            normalized_power=200,
            aerobic_decoupling=6.0,
        ),
    ]

    result = estimate_aerobic_response_from_activities(
        activities,
        reference_date=date(2026, 1, 10),
    )

    assert result == AerobicResponse.UNKNOWN

def test_estimate_response_ignores_future_activities():
    activities = [
        Activity(
            date=date(2026, 1, day),
            duration_minutes=60,
            average_power=180,
            normalized_power=200,
            aerobic_decoupling=decoupling,
        )
        for day, decoupling in [
            (1, 3.0),
            (2, 4.0),
            (3, 5.0),
            (15, 20.0),
        ]
    ]

    result = estimate_aerobic_response_from_activities(
        activities,
        reference_date=date(2026, 1, 10),
    )

    assert result == AerobicResponse.STABLE
