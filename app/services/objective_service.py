from datetime import date

from app.config.objective_rules import (
    OBJECTIVE_PRIORITIES,
    RACE_PHASE_PRIORITIES,
    RACE_PHASE_DAY_LIMITS,
)

from app.models.cyclist import Cyclist
from app.models.training_objective import Objective, RacePhase


def calculate_race_phase(
    objective: Objective,
    objective_date: date | None,
    reference_date: date,
) -> RacePhase | None:
    """
    Calculate the race phase based on the cyclist's objective and the number of days until the race.
    If the objective is not RACE, return None. If the objective date is not provided, raise a ValueError. If the objective date is in the past, raise a ValueError.

    Args:
        objective (Objective): The cyclist's training objective.
        objective_date (date | None): The date of the race, if applicable.
        reference_date (date): The date from which to calculate the number of days until the race
    Returns:
        RacePhase | None: The calculated race phase, or None
        if the objective is not RACE.
    Raises:
        ValueError: If the objective date is not provided for RACE objective or if the objective date is in the past.
    """
    if objective != Objective.RACE:
        return None

    if objective_date is None:
        raise ValueError(
            "Objective date is required for RACE objective"
        )

    days_until_race = (
        objective_date - reference_date
    ).days

    if days_until_race < 0:
        raise ValueError(
            "Objective date cannot be in the past"
        )

    if days_until_race <= RACE_PHASE_DAY_LIMITS[
        RacePhase.TAPER
    ]:
        return RacePhase.TAPER

    if days_until_race <= RACE_PHASE_DAY_LIMITS[
        RacePhase.PEAK
    ]:
        return RacePhase.PEAK

    if days_until_race <= RACE_PHASE_DAY_LIMITS[
        RacePhase.BUILD
    ]:
        return RacePhase.BUILD

    return RacePhase.BASE

def get_objective_priorities(
    cyclist: Cyclist,
    reference_date: date,
):
    """
    Get the priority of the cyclist's objective based on their training objective and race phase.

    Args:
        cyclist (Cyclist): The cyclist object containing the training objective and objective date.
        reference_date (date): The date from which to calculate the race phase if the objective is RACE.

    Returns:
        dict[WorkoutType, int]: Priority assigned to each workout type.

    Raises:
        ValueError: If the cyclist's objective is unsupported.
    """
    if cyclist.objective in {
        Objective.ENDURANCE,
        Objective.PERFORMANCE,
    }:
        return OBJECTIVE_PRIORITIES[
            cyclist.objective
        ]

    if cyclist.objective == Objective.RACE:
        race_phase = calculate_race_phase(
            objective=cyclist.objective,
            objective_date=cyclist.objective_date,
            reference_date=reference_date,
        )

        return RACE_PHASE_PRIORITIES[
            race_phase
        ]

    raise ValueError(
        f"Unsupported objective: {cyclist.objective.value}"
    )