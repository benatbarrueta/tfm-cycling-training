from datetime import date

from app.models.activity import Activity
from app.models.cyclist import Cyclist, Level, Modality
from app.models.training_objective import Objective
from app.services.cold_start_service import (
    calculate_initial_target_tss,
    has_sufficient_training_history,
)


def test_history_is_sufficient():
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
            average_power=185,
            normalized_power=210,
        ),

        # Última semana completa: 7 - 13 sep
        Activity(
            date=date(2026, 9, 8),
            duration_minutes=60,
            average_power=190,
            normalized_power=210,
        ),
        Activity(
            date=date(2026, 9, 11),
            duration_minutes=60,
            average_power=195,
            normalized_power=220,
        ),
    ]

    result = has_sufficient_training_history(
        activities=activities,
        reference_date=date(2026, 9, 16),
    )

    assert result is True


def test_history_is_not_sufficient():
    activities = [
        Activity(
            date=date(2026, 9, 15),
            duration_minutes=60,
            average_power=190,
            normalized_power=210,
        ),
    ]

    result = has_sufficient_training_history(
        activities=activities,
        reference_date=date(2026, 9, 16),
    )

    assert result is False


def test_history_without_power_or_tss_uses_cold_start():
    activities = [
        Activity(
            date=date(2026, 9, day),
            duration_minutes=60,
            average_power=None,
            normalized_power=None,
        )
        for day in (1, 4, 8, 11)
    ]

    result = has_sufficient_training_history(
        activities=activities,
        reference_date=date(2026, 9, 16),
    )

    assert result is False


def test_calculate_initial_target_tss_intermediate():
    cyclist = Cyclist(
        cyclist_id=1,
        modalities=[Modality.XCO],
        level=Level.INTERMEDIATE,
        ftp=250,
        weekly_hours=8,
        available_days=[
            "TUESDAY",
            "WEDNESDAY",
            "FRIDAY",
            "SUNDAY",
        ],
        objective=Objective.PERFORMANCE,
    )

    result = calculate_initial_target_tss(
        cyclist=cyclist,
    )

    assert result == 288
