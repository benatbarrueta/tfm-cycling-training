from datetime import date

import pytest

from app.models.cyclist import Cyclist, Level, Modality
from app.models.workout import WorkoutType
from app.models.training_objective import (
    Objective,
    RacePhase,
)

from app.services.objective_service import (
    calculate_race_phase,
    get_objective_priorities,
)


def test_calculate_taper_phase():
    result = calculate_race_phase(
        objective=Objective.RACE,
        objective_date=date(2026, 9, 26),
        reference_date=date(2026, 9, 16),
    )

    assert result == RacePhase.TAPER


def test_calculate_peak_phase():
    result = calculate_race_phase(
        objective=Objective.RACE,
        objective_date=date(2026, 10, 20),
        reference_date=date(2026, 9, 16),
    )

    assert result == RacePhase.PEAK


def test_calculate_build_phase():
    result = calculate_race_phase(
        objective=Objective.RACE,
        objective_date=date(2026, 12, 15),
        reference_date=date(2026, 9, 16),
    )

    assert result == RacePhase.BUILD


def test_calculate_base_phase():
    result = calculate_race_phase(
        objective=Objective.RACE,
        objective_date=date(2027, 3, 1),
        reference_date=date(2026, 9, 16),
    )

    assert result == RacePhase.BASE

def test_race_requires_objective_date():
    with pytest.raises(
        ValueError,
        match="Objective date is required",
    ):
        calculate_race_phase(
            objective=Objective.RACE,
            objective_date=None,
            reference_date=date(2026, 9, 16),
        )


def test_race_date_cannot_be_in_past():
    with pytest.raises(
        ValueError,
        match="cannot be in the past",
    ):
        calculate_race_phase(
            objective=Objective.RACE,
            objective_date=date(2026, 9, 1),
            reference_date=date(2026, 9, 16),
        )

def test_non_race_objective_has_no_phase():
    result = calculate_race_phase(
        objective=Objective.ENDURANCE,
        objective_date=None,
        reference_date=date(2026, 9, 16),
    )

    assert result is None

def test_get_endurance_priorities():
    cyclist = Cyclist(
        cyclist_id=1,
        modalities=[Modality.XCM],
        level=Level.INTERMEDIATE,
        ftp=250,
        weekly_hours=8,
        available_days=[
            "TUESDAY",
            "THURSDAY",
            "SATURDAY",
            "SUNDAY",
        ],
        objective=Objective.ENDURANCE,
    )

    priorities = get_objective_priorities(
        cyclist=cyclist,
        reference_date=date(2026, 9, 16),
    )

    assert (
        priorities[WorkoutType.ENDURANCE]
        > priorities[WorkoutType.VO2MAX]
    )

def test_get_race_peak_priorities():
    cyclist = Cyclist(
        cyclist_id=1,
        modalities=[Modality.XCO],
        level=Level.INTERMEDIATE,
        ftp=250,
        weekly_hours=8,
        available_days=[
            "TUESDAY",
            "THURSDAY",
            "SATURDAY",
            "SUNDAY",
        ],
        objective=Objective.RACE,
        objective_date=date(2026, 10, 10),
    )

    priorities = get_objective_priorities(
        cyclist=cyclist,
        reference_date=date(2026, 9, 16),
    )

    assert priorities is not None
    assert WorkoutType.VO2MAX in priorities