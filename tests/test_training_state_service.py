from datetime import date

import pytest

from app.models.activity import Activity
from app.models.training_state import LoadTrend
from app.services.training_state_service import (
    build_training_state_from_activities,
)

def test_build_training_state_from_activities():
    activities = [
        # Semana completa anterior: 31 ago - 6 sep
        Activity(
            date=date(2026, 9, 1),
            duration_minutes=60,
            average_power=180,
            normalized_power=200,
        ),
        Activity(
            date=date(2026, 9, 4),
            duration_minutes=60,
            average_power=190,
            normalized_power=225,
        ),

        # Última semana completa: 7 - 13 sep
        Activity(
            date=date(2026, 9, 7),
            duration_minutes=60,
            average_power=190,
            normalized_power=200,
        ),
        Activity(
            date=date(2026, 9, 10),
            duration_minutes=60,
            average_power=200,
            normalized_power=225,
        ),
        Activity(
            date=date(2026, 9, 12),
            duration_minutes=60,
            average_power=210,
            normalized_power=250,
        ),

        # Semana actual: debe ignorarse
        Activity(
            date=date(2026, 9, 15),
            duration_minutes=60,
            average_power=210,
            normalized_power=250,
        ),
    ]

    state = build_training_state_from_activities(
        activities=activities,
        reference_date=date(2026, 9, 16),
        ftp=250,
    )

    assert state.weekly_tss == 245
    assert state.previous_week_tss == 145
    assert state.load_trend == LoadTrend.INCREASING
    assert state.training_frequency == 3


def test_training_state_skips_activity_without_power_in_mixed_history():
    activities = [
        Activity(date=date(2026, 9, 7), duration_minutes=60, average_power=180, normalized_power=200),
        Activity(date=date(2026, 9, 8), duration_minutes=45, average_power=None, normalized_power=None),
        Activity(date=date(2026, 9, 1), duration_minutes=60, average_power=180, normalized_power=200),
    ]

    state = build_training_state_from_activities(
        activities=activities,
        reference_date=date(2026, 9, 16),
        ftp=250,
    )

    assert state.weekly_tss == pytest.approx(64)
    assert state.previous_week_tss == pytest.approx(64)
    assert state.training_frequency == 2
