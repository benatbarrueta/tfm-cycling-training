from datetime import date, timedelta

from app.config.cold_start_rules import (
    COLD_START_ESTIMATED_IF,
    MIN_ACTIVITIES_CURRENT_WEEK,
    MIN_ACTIVITIES_PREVIOUS_WEEK,
)
from app.models.activity import Activity
from app.models.cyclist import Cyclist


def has_sufficient_training_history(
    activities: list[Activity],
    reference_date: date,
) -> bool:
    """
    Check if the cyclist has sufficient training history based on the number of activities in the current and previous weeks.

    Args:
        activities (list[Activity]): The list of activities to check.
        reference_date (date): The date to use as a reference for the current and previous weeks

    Returns:
        bool: True if the cyclist has sufficient training history, False otherwise.

    Raises:
        ValueError: If the reference date is not provided.
    """

    reference_week_start = (
        reference_date
        - timedelta(days=reference_date.weekday())
    )

    current_week_start = (
        reference_week_start
        - timedelta(days=7)
    )

    previous_week_start = (
        current_week_start
        - timedelta(days=7)
    )

    def has_tss_input(activity: Activity) -> bool:
        return activity.tss is not None or (
            activity.normalized_power is not None
            and activity.normalized_power > 0
            and activity.duration_minutes is not None
            and activity.duration_minutes > 0
        )

    current_week_count = sum(
        1
        for activity in activities
        if current_week_start
        <= activity.date
        < reference_week_start
        and has_tss_input(activity)
    )

    previous_week_count = sum(
        1
        for activity in activities
        if previous_week_start
        <= activity.date
        < current_week_start
        and has_tss_input(activity)
    )

    return (
        current_week_count >= MIN_ACTIVITIES_CURRENT_WEEK
        and previous_week_count >= MIN_ACTIVITIES_PREVIOUS_WEEK
    )


def calculate_initial_target_tss(
    cyclist: Cyclist,
) -> float:
    """
    Calculate the initial target TSS for a cyclist based on their level and weekly hours.

    Args:
        cyclist (Cyclist): The cyclist for whom to calculate the initial target TSS.

    Returns:
        float: The calculated initial target TSS.

    Raises:
        ValueError: If the cyclist's weekly hours are less than or equal to 0.
    """
    if cyclist.weekly_hours <= 0:
        raise ValueError(
            "Cyclist weekly hours must be greater than 0"
        )

    estimated_if = COLD_START_ESTIMATED_IF[
        cyclist.level
    ]

    target_tss = (
        cyclist.weekly_hours
        * estimated_if ** 2
        * 100
    )

    return round(target_tss, 2)
