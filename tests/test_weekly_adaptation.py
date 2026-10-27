from datetime import date, datetime

import pytest
from sqlalchemy import create_engine, func, select
from sqlalchemy.orm import Session

from app.activities.service import available_workouts, link_to_workout
from app.core.config import Settings
from app.database.base import Base
from app.database.models import (
    ActivityRecord,
    AdaptationEvent,
    CyclistProfile,
    PlannedWeek,
    PlannedWorkout,
    SeasonPlan,
    TrainingPhase,
    User,
    WeeklyReview,
    utc_now,
)
from app.season.service import (
    _rpe_adaptation,
    advance_plan,
    list_adaptations,
    monday_on_or_after,
    preview_week_review,
    recalculate_week_review,
)
from app.season.schemas import AdvanceSeasonPlanRead, WeeklyReviewPreviewRead
from app.season.weekly_review import summarize_completed_week


def build_week() -> tuple[PlannedWeek, PlannedWorkout]:
    week = PlannedWeek(
        position=1,
        week_start=date(2026, 10, 5),
        week_end=date(2026, 10, 11),
        status="ACTIVE",
        focus="BASE",
        provisional_target_tss=100,
        provisional_hours=2,
        adapted_target_tss=100,
    )
    workout = PlannedWorkout(
        position=1,
        scheduled_date=date(2026, 10, 6),
        day="TUESDAY",
        workout_type="ENDURANCE",
        target_tss=100,
        estimated_tss=100,
        duration_minutes=120,
    )
    week.workouts = [workout]
    return week, workout


@pytest.mark.parametrize(
    ("reference", "expected"),
    [
        (date(2026, 10, 26), date(2026, 10, 26)),
        (date(2026, 10, 27), date(2026, 11, 2)),
        (date(2026, 11, 1), date(2026, 11, 2)),
    ],
)
def test_training_week_starts_on_current_or_next_monday(reference, expected):
    assert monday_on_or_after(reference) == expected


def test_weekly_summary_counts_all_load_and_only_linked_adherence():
    week, workout = build_week()
    linked = ActivityRecord(
        title="Sesión prevista",
        started_at=datetime(2026, 10, 6, 8),
        sport="CYCLING",
        duration_minutes=60,
        tss=50,
        aerobic_decoupling=4,
        source="MANUAL",
        planned_workout=workout,
    )
    extra = ActivityRecord(
        title="Actividad adicional",
        started_at=datetime(2026, 10, 8, 8),
        sport="CYCLING",
        duration_minutes=30,
        tss=None,
        perceived_exertion=7,
        aerobic_decoupling=8,
        source="MANUAL",
    )

    result = summarize_completed_week(week, [linked, extra])

    assert result.registered_tss == pytest.approx(50)
    assert result.linked_workout_count == 1
    assert result.completed_activity_count == 2
    assert result.activities_without_tss == 1
    assert result.tss_coverage == pytest.approx(0.5)
    assert result.registered_rpe_load == pytest.approx(210)
    assert result.median_perceived_exertion == pytest.approx(7)
    assert result.activities_with_rpe_load == 1
    assert result.activities_without_load == 0
    assert result.median_aerobic_decoupling == pytest.approx(6)


def test_rpe_fallback_reduces_load_after_a_hard_week():
    week, workout = build_week()
    activity = ActivityRecord(
        title="Sesión exigente",
        started_at=datetime(2026, 10, 6, 8),
        sport="CYCLING",
        duration_minutes=130,
        perceived_exertion=9,
        source="MANUAL",
        planned_workout=workout,
    )
    completion = summarize_completed_week(week, [activity])

    decision, target = _rpe_adaptation(completion, 110)

    assert decision.value == "REDUCE"
    assert target == pytest.approx(93.5)


def test_advance_plan_is_transactional_and_idempotent():
    engine = create_engine("sqlite://")
    Base.metadata.create_all(engine)
    with Session(engine) as db:
        user = User(email="rider@example.com", display_name="Rider", is_demo=True)
        db.add(user)
        db.flush()
        profile = CyclistProfile(
            user_id=user.id,
            ftp=250,
            weekly_hours=6,
            available_days=["TUESDAY", "THURSDAY", "SUNDAY"],
            modality="XCO",
            level="INTERMEDIATE",
            objective="PERFORMANCE",
            target_date=date(2026, 12, 20),
            timezone="Europe/Madrid",
            onboarding_completed_at=utc_now(),
        )
        plan = SeasonPlan(
            user_id=user.id,
            name="Temporada",
            status="ACTIVE",
            start_date=date(2026, 10, 5),
            target_date=date(2026, 12, 20),
            objective="PERFORMANCE",
            modality="XCO",
            level="INTERMEDIATE",
            ftp_snapshot=250,
            weekly_hours_snapshot=6,
            available_days_snapshot=["TUESDAY", "THURSDAY", "SUNDAY"],
            generator_version="test",
        )
        phase = TrainingPhase(
            season_plan=plan,
            phase_type="BASE",
            position=1,
            start_date=date(2026, 10, 5),
            end_date=date(2026, 10, 18),
            week_count=2,
        )
        first, workout = build_week()
        first.season_plan = plan
        first.training_phase = phase
        second = PlannedWeek(
            season_plan=plan,
            training_phase=phase,
            position=2,
            week_start=date(2026, 10, 12),
            week_end=date(2026, 10, 18),
            status="PROVISIONAL",
            focus="BASE",
            provisional_target_tss=105,
            provisional_hours=6,
        )
        activity = ActivityRecord(
            user_id=user.id,
            planned_workout=workout,
            title="Salida",
            started_at=datetime(2026, 10, 6, 8),
            sport="CYCLING",
            duration_minutes=60,
            tss=70,
            aerobic_decoupling=4,
            source="MANUAL",
        )
        db.add_all([profile, plan, phase, first, second, activity])
        db.commit()

        preview = preview_week_review(
            db,
            user.id,
            profile,
            reference=date(2026, 10, 12),
        )
        assert preview["week_id"] == first.id
        assert preview["registered_tss"] == pytest.approx(70)
        assert preview["completed_workout_count"] == 1
        assert preview["activities_without_tss"] == 0
        assert preview["activities_without_response"] == 0
        assert preview["pending_overdue_weeks"] == 1
        WeeklyReviewPreviewRead.model_validate(preview)
        assert db.scalar(select(func.count()).select_from(WeeklyReview)) == 0
        assert db.scalar(select(func.count()).select_from(AdaptationEvent)) == 0

        result = advance_plan(
            db,
            user,
            profile,
            Settings(app_env="test", session_secret="test"),
            reference=date(2026, 10, 12),
        )

        assert result["status"] == "ADVANCED"
        assert result["completed_week"].status == "COMPLETED"
        assert result["active_week"].status == "ACTIVE"
        assert result["completed_week"].review.registered_tss == pytest.approx(70)
        assert len(result["active_week"].workouts) == 3
        response = AdvanceSeasonPlanRead.model_validate(result)
        assert response.adaptation.response_classification == "STABLE"
        assert "previsión de temporada" in response.adaptation.reason
        assert "revisión solicitó" in response.adaptation.reason

        repeated = advance_plan(
            db,
            user,
            profile,
            Settings(app_env="test", session_secret="test"),
            reference=date(2026, 10, 12),
        )
        assert repeated["already_processed"] is True
        assert db.scalar(select(func.count()).select_from(WeeklyReview)) == 1
        assert db.scalar(select(func.count()).select_from(AdaptationEvent)) == 1
        adaptations = list_adaptations(db, user.id, plan.id)
        assert len(adaptations) == 1
        assert adaptations[0].source_week_id == first.id
        assert adaptations[0].target_week_id == second.id
        assert adaptations[0].provisional_target_tss == pytest.approx(105)
        assert adaptations[0].adapted_target_tss is not None

        activity.tss = 85
        activity.aerobic_decoupling = 6
        db.commit()
        corrected = recalculate_week_review(db, user.id, profile, first.id)
        assert corrected.registered_tss == pytest.approx(85)
        assert corrected.response_median == pytest.approx(6)
        assert db.scalar(select(func.count()).select_from(AdaptationEvent)) == 1

        options = available_workouts(db, user.id, workout.scheduled_date)
        assert len(options) == 1
        assert options[0]["already_linked"] is True
        assert options[0]["linked_activity_id"] == activity.id

        extra_activity = ActivityRecord(
            user_id=user.id,
            title="Otra salida",
            started_at=datetime(2026, 10, 6, 10),
            sport="CYCLING",
            duration_minutes=30,
            tss=20,
            source="MANUAL",
        )
        db.add(extra_activity)
        db.commit()

        with pytest.raises(
            ValueError,
            match="ya está vinculada",
        ):
            link_to_workout(
                db,
                user.id,
                extra_activity.id,
                workout.id,
                profile.timezone,
            )
