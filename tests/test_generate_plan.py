from datetime import date

import pytest

from app.generate_plan import (
    calculate_default_reference_date,
)
from app.models.activity import Activity


def make_activity(activity_date: date) -> Activity:
    return Activity(
        date=activity_date,
        duration_minutes=60,
        average_power=180,
        normalized_power=200,
    )

def test_calculate_default_reference_date():
    activities = [
        make_activity(date(2026, 1, 3)),
        make_activity(date(2026, 1, 7)),
        make_activity(date(2026, 1, 11)),
    ]

    result = calculate_default_reference_date(
        activities
    )

    assert result == date(2026, 1, 12)

def test_reference_date_after_activity_on_monday():
    activities = [
        make_activity(date(2026, 1, 12)),
    ]

    result = calculate_default_reference_date(
        activities
    )

    assert result == date(2026, 1, 19)

def test_reference_date_requires_activities():
    with pytest.raises(ValueError):
        calculate_default_reference_date([])