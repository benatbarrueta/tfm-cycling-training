from datetime import date, timedelta

from app.models.activity import Activity
from app.models.training_state import TrainingState
from app.services.metrics import (
    calculate_activity_metrics,
    calculate_weekly_tss,
    calculate_load_trend,
)

def build_training_state_from_activities(
    activities: list[Activity],
    reference_date: date,
    ftp: float
) -> TrainingState:
    """
    Build a TrainingState object based on a list of activities and a reference date.

    Args:
        activities (list[Activity]): A list of Activity objects.
        reference_date (date): The reference date to determine the current and previous weeks.

    Returns:
        TrainingState: An object representing the training state, including weekly TSS, previous week's TSS, load trend, and training frequency.
    """

    reference_week_start = (
        reference_date - timedelta(days=reference_date.weekday())
    )
    # Monday of the current week
    current_week_start = (
        reference_week_start - timedelta(days=7)
    )

    # Monday of the previous week
    previous_week_start = (
        current_week_start - timedelta(days=7)
    )

    # Activities in the current week
    current_week_activities = [
        activity 
        for activity in activities
        if current_week_start <= activity.date < reference_week_start
    ]

    # Activities in the previous week
    previous_week_activities = [
        activity 
        for activity in activities
        if previous_week_start <= activity.date < current_week_start
    ]

    # Calculate TSS for current week activities
    current_week_tss = [
        get_or_calculate_activity_tss(activity, ftp)
        for activity in current_week_activities
    ]

    # Calculate TSS for previous week activities
    previous_week_tss = [
        get_or_calculate_activity_tss(activity, ftp)
        for activity in previous_week_activities
    ]

    weekly_tss = calculate_weekly_tss(current_week_tss)
    previous_tss = calculate_weekly_tss(previous_week_tss)

    load_trend = calculate_load_trend(
        weekly_tss=weekly_tss,
        previous_week_tss=previous_tss,
    )

    return TrainingState(
        weekly_tss=weekly_tss,
        previous_week_tss=previous_tss,
        load_trend=load_trend,
        training_frequency=len(current_week_activities),
    )


def get_or_calculate_activity_tss(
    activity: Activity, 
    ftp: float
) -> float:
    """
    Get the TSS of an activity. If the TSS is not already calculated, calculate it.

    Args:
        activity (Activity): The activity for which to get or calculate the TSS.
        ftp (float): The functional threshold power of the cyclist.

    Returns:
        float: The TSS of the activity.
    """
    if activity.tss is None:
        calculate_activity_metrics(
            activity=activity,
            ftp=ftp,
        )

    if activity.tss is None:
        raise ValueError(
            f"Could not calculate TSS for activity from {activity.date}"
        )

    return activity.tss
