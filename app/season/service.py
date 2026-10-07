from datetime import date, timedelta
from pathlib import Path
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.activities.adapter import to_domain_activity
from app.core.config import Settings
from app.data.response_model import load_response_model_artifact
from app.database.models import (
    ActivityRecord,
    CyclistProfile,
    PlannedWeek,
    PlannedWorkout,
    SeasonPlan,
    TrainingPhase,
    User,
    utc_now,
)
from app.models.cyclist import Cyclist, Level, Modality
from app.models.training_objective import Objective
from app.services.training_engine_service import generate_personalized_training_plan
from app.services.training_plan_summary_service import build_training_plan_summary

PHASES = ("BASE", "BUILD", "PEAK", "TAPER")
GENERATOR_VERSION = "deterministic-season-v1"


def next_monday(reference: date) -> date:
    days_until_monday = (7 - reference.weekday()) % 7
    return reference + timedelta(days=days_until_monday or 7)


def phase_distribution(weeks: int) -> list[int]:
    if weeks < 4:
        raise ValueError("La fecha objetivo debe dejar al menos cuatro semanas.")
    raw = [weeks * 0.35, weeks * 0.40, weeks * 0.15, weeks * 0.10]
    counts = [max(1, int(value)) for value in raw]
    while sum(counts) > weeks:
        index = max(range(4), key=lambda item: (counts[item], -item))
        if counts[index] > 1:
            counts[index] -= 1
        else:
            break
    while sum(counts) < weeks:
        index = max(range(4), key=lambda item: (raw[item] - counts[item], -item))
        counts[index] += 1
    return counts


def _activity_domains(db: Session, user_id: UUID, timezone_name: str):
    records = db.scalars(select(ActivityRecord).where(ActivityRecord.user_id == user_id)).all()
    return [to_domain_activity(record, timezone_name) for record in records]


def _workout_data(workout, summary: dict, position: int, scheduled_date: date) -> dict:
    prediction = next(
        (item for item in summary["workout_response_predictions"] if item["day"] == workout.day),
        None,
    )
    return {
        "position": position,
        "scheduled_date": scheduled_date,
        "day": workout.day,
        "workout_type": workout.workout_type.value,
        "target_tss": workout.target_tss,
        "estimated_tss": workout.estimated_tss,
        "duration_minutes": workout.duration_minutes,
        "target_power_min": workout.target_power_min,
        "target_power_max": workout.target_power_max,
        "warmup": summary["workouts"][position - 1]["warmup"],
        "intervals": summary["workouts"][position - 1]["intervals"],
        "cooldown": summary["workouts"][position - 1]["cooldown"],
        "predicted_aerobic_decoupling": prediction["predicted_aerobic_decoupling"] if prediction else None,
        "aerobic_response": prediction["aerobic_response"] if prediction else None,
        "outside_training_range_features": prediction["outside_training_range_features"] if prediction else None,
    }


def create_plan(db: Session, user: User, profile: CyclistProfile, name: str, settings: Settings, reference: date | None = None) -> SeasonPlan:
    existing = db.scalar(select(SeasonPlan).where(SeasonPlan.user_id == user.id, SeasonPlan.status == "ACTIVE"))
    if existing:
        raise RuntimeError("Ya existe un plan activo para este usuario.")
    if profile.target_date is None:
        raise ValueError("El perfil debe tener una fecha objetivo para crear el plan.")
    today = reference or date.today()
    start = next_monday(today)
    last_start = profile.target_date - timedelta(days=profile.target_date.weekday())
    weeks_count = ((last_start - start).days // 7) + 1
    counts = phase_distribution(weeks_count)
    plan = SeasonPlan(
        user_id=user.id, name=name.strip() or "Plan de temporada", status="ACTIVE",
        start_date=start, target_date=profile.target_date, objective=profile.objective,
        modality=profile.modality, level=profile.level, ftp_snapshot=profile.ftp,
        weekly_hours_snapshot=profile.weekly_hours, available_days_snapshot=profile.available_days,
        generator_version=GENERATOR_VERSION,
    )
    db.add(plan)
    current = start
    phases = []
    phase_by_week = []
    for position, (phase_type, count) in enumerate(zip(PHASES, counts), start=1):
        phase = TrainingPhase(
            season_plan=plan, phase_type=phase_type, position=position,
            start_date=current, end_date=current + timedelta(days=count * 7 - 1), week_count=count,
        )
        db.add(phase)
        phases.append(phase)
        phase_by_week.extend([phase] * count)
        current += timedelta(days=count * 7)
    db.flush()
    activities = _activity_domains(db, user.id, profile.timezone)
    cyclist = Cyclist(
        cyclist_id=1, modalities=[Modality(profile.modality)], level=Level(profile.level),
        ftp=profile.ftp, weekly_hours=profile.weekly_hours,
        available_days=profile.available_days, objective=Objective(profile.objective),
        objective_date=profile.target_date,
    )
    artifact_path = Path("artifacts/response_balanced_linear.json")
    artifact = load_response_model_artifact(artifact_path) if artifact_path.exists() and activities else None
    active_domain_plan = generate_personalized_training_plan(
        cyclist, Modality(profile.modality), activities, start, response_model_artifact=artifact,
    )
    active_summary = build_training_plan_summary(active_domain_plan)
    provisional_tss = active_summary["target_tss"]
    for index in range(weeks_count):
        week_start = start + timedelta(days=index * 7)
        phase = phase_by_week[index]
        multiplier = 1 + min(index, 3) * 0.05
        if phase.phase_type == "TAPER":
            multiplier = max(0.6, 0.85 - (index - (weeks_count - counts[-1])) * 0.05)
        week = PlannedWeek(
            season_plan=plan, training_phase=phase, position=index + 1,
            week_start=week_start, week_end=week_start + timedelta(days=6),
            status="ACTIVE" if index == 0 else "PROVISIONAL", focus=phase.phase_type,
            provisional_target_tss=round(provisional_tss * multiplier, 2),
            provisional_hours=profile.weekly_hours,
            requested_target_tss=active_summary["requested_target_tss"] if index == 0 else None,
            adapted_target_tss=active_summary["target_tss"] if index == 0 else None,
            estimated_total_tss=active_summary["estimated_total_tss"] if index == 0 else None,
            expected_aerobic_decoupling=active_summary["expected_aerobic_decoupling"] if index == 0 else None,
            response_prediction_method=active_summary["response_prediction_method"] if index == 0 else None,
            load_decision=active_summary["load_decision"] if index == 0 else None,
            generated_at=utc_now() if index == 0 else None,
        )
        db.add(week)
        db.flush()
        if index == 0:
            for workout_position, workout in enumerate(active_domain_plan.workouts, start=1):
                scheduled = week_start + timedelta(days=__import__("app.services.training_plan_service", fromlist=["DAY_ORDER"]).DAY_ORDER[workout.day])
                db.add(PlannedWorkout(planned_week=week, **_workout_data(workout, active_summary, workout_position, scheduled)))
    db.commit()
    return get_plan(db, user.id, plan.id)


def get_plan(db: Session, user_id: UUID, plan_id: UUID | None = None):
    query = select(SeasonPlan).options(
        selectinload(SeasonPlan.phases),
        selectinload(SeasonPlan.weeks).selectinload(PlannedWeek.training_phase),
        selectinload(SeasonPlan.weeks).selectinload(PlannedWeek.workouts),
    ).where(SeasonPlan.user_id == user_id)
    if plan_id is not None:
        query = query.where(SeasonPlan.id == plan_id)
    else:
        query = query.where(SeasonPlan.status == "ACTIVE")
    return db.scalar(query)
