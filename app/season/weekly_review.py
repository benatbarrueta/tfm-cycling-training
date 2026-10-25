"""Weekly completion summaries used by the adaptive planning loop."""

from dataclasses import dataclass
from statistics import median

from app.database.models import ActivityRecord, PlannedWeek


@dataclass(frozen=True)
class WeeklyCompletionSummary:
    planned_workout_count: int
    linked_workout_count: int
    completed_activity_count: int
    planned_tss: float
    registered_tss: float
    activities_with_tss: int
    activities_without_tss: int
    tss_coverage: float
    planned_duration_minutes: float
    registered_duration_minutes: float
    workout_completion_rate: float
    tss_completion_ratio: float | None
    median_aerobic_decoupling: float | None
    responses_available: int


def summarize_completed_week(
    planned_week: PlannedWeek,
    activities: list[ActivityRecord],
) -> WeeklyCompletionSummary:
    """Compare a planned week with every activity recorded in its date range."""
    workout_ids = {workout.id for workout in planned_week.workouts}
    linked_workout_ids = {
        activity.planned_workout_id
        for activity in activities
        if activity.planned_workout_id in workout_ids
    }
    known_tss = [float(activity.tss) for activity in activities if activity.tss is not None]
    responses = [
        float(activity.aerobic_decoupling)
        for activity in activities
        if activity.aerobic_decoupling is not None
    ]
    planned_tss = float(
        planned_week.adapted_target_tss
        or planned_week.estimated_total_tss
        or planned_week.provisional_target_tss
    )
    planned_duration = float(
        sum(workout.duration_minutes or 0 for workout in planned_week.workouts)
    )
    registered_tss = sum(known_tss)
    activity_count = len(activities)
    planned_count = len(planned_week.workouts)

    return WeeklyCompletionSummary(
        planned_workout_count=planned_count,
        linked_workout_count=len(linked_workout_ids),
        completed_activity_count=activity_count,
        planned_tss=planned_tss,
        registered_tss=registered_tss,
        activities_with_tss=len(known_tss),
        activities_without_tss=activity_count - len(known_tss),
        tss_coverage=(len(known_tss) / activity_count) if activity_count else 0.0,
        planned_duration_minutes=planned_duration,
        registered_duration_minutes=sum(float(activity.duration_minutes) for activity in activities),
        workout_completion_rate=(len(linked_workout_ids) / planned_count) if planned_count else 0.0,
        tss_completion_ratio=(registered_tss / planned_tss) if planned_tss > 0 else None,
        median_aerobic_decoupling=float(median(responses)) if responses else None,
        responses_available=len(responses),
    )

