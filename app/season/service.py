from datetime import date, datetime, time, timedelta, timezone
from pathlib import Path
from uuid import UUID
from zoneinfo import ZoneInfo

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.activities.adapter import to_domain_activity
from app.core.config import Settings
from app.data.response_model import load_response_model_artifact
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
from app.models.cyclist import Cyclist, Level, Modality
from app.models.aerobic_response import AerobicResponse
from app.models.load_decision import LoadDecision
from app.models.training_objective import Objective
from app.services.training_engine_service import generate_personalized_training_plan
from app.services.aerobic_response_service import classify_aerobic_response
from app.services.training_plan_service import DAY_ORDER, generate_feasible_training_plan
from app.services.training_plan_summary_service import build_training_plan_summary
from app.season.weekly_review import summarize_completed_week

PHASES = ("BASE", "BUILD", "PEAK", "TAPER")
GENERATOR_VERSION = "deterministic-season-v1"
ADAPTATION_RULE_VERSION = "weekly-review-v2"
POWER_TSS = "POWER_TSS"
RPE_FALLBACK = "RPE_FALLBACK"
INSUFFICIENT_DATA = "INSUFFICIENT_DATA"


def monday_on_or_after(reference: date) -> date:
    days_until_monday = (7 - reference.weekday()) % 7
    return reference + timedelta(days=days_until_monday)


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
    start = monday_on_or_after(today)
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
                scheduled = week_start + timedelta(days=DAY_ORDER[workout.day])
                db.add(PlannedWorkout(planned_week=week, **_workout_data(workout, active_summary, workout_position, scheduled)))
    db.commit()
    return get_plan(db, user.id, plan.id)


def get_plan(db: Session, user_id: UUID, plan_id: UUID | None = None):
    query = select(SeasonPlan).options(
        selectinload(SeasonPlan.phases),
        selectinload(SeasonPlan.weeks).selectinload(PlannedWeek.training_phase),
        selectinload(SeasonPlan.weeks).selectinload(PlannedWeek.workouts),
        selectinload(SeasonPlan.weeks).selectinload(PlannedWeek.review),
    ).where(SeasonPlan.user_id == user_id)
    if plan_id is not None:
        query = query.where(SeasonPlan.id == plan_id)
    else:
        query = query.where(SeasonPlan.status == "ACTIVE")
    return db.scalar(query)


def mark_overdue_week_pending_review(
    db: Session,
    user_id: UUID,
    reference: date | None = None,
) -> SeasonPlan | None:
    """Move an elapsed active week to review without closing or adapting it."""
    plan = get_plan(db, user_id)
    if plan is None:
        return None
    today = reference or date.today()
    changed = False
    for week in plan.weeks:
        if week.status == "ACTIVE" and week.week_end < today:
            week.status = "PENDING_REVIEW"
            changed = True
    if changed:
        db.commit()
        return get_plan(db, user_id, plan.id)
    return plan


def list_plans(db: Session, user_id: UUID) -> list[SeasonPlan]:
    return list(
        db.scalars(
            select(SeasonPlan)
            .options(
                selectinload(SeasonPlan.phases),
                selectinload(SeasonPlan.weeks).selectinload(PlannedWeek.training_phase),
                selectinload(SeasonPlan.weeks).selectinload(PlannedWeek.workouts),
                selectinload(SeasonPlan.weeks).selectinload(PlannedWeek.review),
            )
            .where(SeasonPlan.user_id == user_id)
            .order_by(SeasonPlan.created_at.desc())
        )
    )


def list_adaptations(db: Session, user_id: UUID, plan_id: UUID) -> list[AdaptationEvent]:
    plan = get_plan(db, user_id, plan_id)
    if plan is None:
        raise LookupError("Plan no encontrado.")
    return list(
        db.scalars(
            select(AdaptationEvent)
            .where(AdaptationEvent.season_plan_id == plan.id)
            .order_by(AdaptationEvent.created_at.desc())
        )
    )


def _utc_week_bounds(week: PlannedWeek, timezone_name: str) -> tuple[datetime, datetime]:
    zone = ZoneInfo(timezone_name)
    local_start = datetime.combine(week.week_start, time.min, tzinfo=zone)
    local_end = datetime.combine(week.week_end + timedelta(days=1), time.min, tzinfo=zone)
    return (
        local_start.astimezone(timezone.utc).replace(tzinfo=None),
        local_end.astimezone(timezone.utc).replace(tzinfo=None),
    )


def preview_week_review(
    db: Session,
    user_id: UUID,
    profile: CyclistProfile,
    reference: date | None = None,
) -> dict:
    plan = get_plan(db, user_id)
    if plan is None:
        raise LookupError("No hay un plan activo.")
    today = reference or date.today()
    overdue = sorted(
        [
            week
            for week in plan.weeks
            if week.status in {"ACTIVE", "PENDING_REVIEW"} and week.week_end < today
        ],
        key=lambda item: item.position,
    )
    if not overdue:
        raise ValueError("No hay semanas terminadas pendientes de revisión.")
    week = overdue[0]
    utc_start, utc_end = _utc_week_bounds(week, profile.timezone)
    activities = list(
        db.scalars(
            select(ActivityRecord).where(
                ActivityRecord.user_id == user_id,
                ActivityRecord.started_at >= utc_start,
                ActivityRecord.started_at < utc_end,
            )
        )
    )
    summary = summarize_completed_week(week, activities)
    return {
        "week_id": week.id,
        "week_start": week.week_start,
        "week_end": week.week_end,
        "planned_tss": summary.planned_tss,
        "registered_tss": summary.registered_tss,
        "planned_duration_minutes": summary.planned_duration_minutes,
        "registered_duration_minutes": summary.registered_duration_minutes,
        "planned_workout_count": summary.planned_workout_count,
        "completed_workout_count": summary.linked_workout_count,
        "activity_count": summary.completed_activity_count,
        "activities_with_tss": summary.activities_with_tss,
        "activities_without_tss": summary.activities_without_tss,
        "registered_rpe_load": summary.registered_rpe_load,
        "median_perceived_exertion": summary.median_perceived_exertion,
        "activities_with_rpe_load": summary.activities_with_rpe_load,
        "activities_without_load": summary.activities_without_load,
        "response_median": summary.median_aerobic_decoupling,
        "response_count": summary.responses_available,
        "activities_without_response": (
            summary.completed_activity_count - summary.responses_available
        ),
        "pending_overdue_weeks": len([
            candidate
            for candidate in plan.weeks
            if candidate.position >= week.position
            and candidate.status in {"ACTIVE", "PENDING_REVIEW", "PROVISIONAL"}
            and candidate.week_end < today
        ]),
    }


def _generate_week(
    db: Session,
    user: User,
    profile: CyclistProfile,
    week: PlannedWeek,
) -> dict:
    activities = _activity_domains(db, user.id, profile.timezone)
    cyclist = Cyclist(
        cyclist_id=1,
        modalities=[Modality(profile.modality)],
        level=Level(profile.level),
        ftp=profile.ftp,
        weekly_hours=profile.weekly_hours,
        available_days=profile.available_days,
        objective=Objective(profile.objective),
        objective_date=profile.target_date,
    )
    artifact_path = Path("artifacts/response_balanced_linear.json")
    artifact = (
        load_response_model_artifact(artifact_path)
        if artifact_path.exists() and activities
        else None
    )
    domain_plan = generate_personalized_training_plan(
        cyclist,
        Modality(profile.modality),
        activities,
        week.week_start,
        response_model_artifact=artifact,
    )
    summary = build_training_plan_summary(domain_plan)
    week.requested_target_tss = summary["requested_target_tss"]
    week.adapted_target_tss = summary["target_tss"]
    week.estimated_total_tss = summary["estimated_total_tss"]
    week.expected_aerobic_decoupling = summary["expected_aerobic_decoupling"]
    week.response_prediction_method = summary["response_prediction_method"]
    week.load_decision = summary["load_decision"]
    week.generated_at = utc_now()
    week.status = "ACTIVE"
    week.workouts.clear()
    db.flush()
    for position, workout in enumerate(domain_plan.workouts, start=1):
        scheduled = week.week_start + timedelta(days=DAY_ORDER[workout.day])
        db.add(
            PlannedWorkout(
                planned_week=week,
                **_workout_data(workout, summary, position, scheduled),
            )
        )
    return summary


def _rpe_adaptation(completion, provisional_target_tss: float) -> tuple[LoadDecision, float]:
    """Apply a conservative load rule without converting RPE into TSS."""
    duration_ratio = (
        completion.registered_duration_minutes / completion.planned_duration_minutes
        if completion.planned_duration_minutes > 0
        else 0.0
    )
    rpe = completion.median_perceived_exertion
    if (rpe is not None and rpe >= 8) or duration_ratio > 1.2:
        return LoadDecision.REDUCE, round(provisional_target_tss * 0.85, 2)
    if completion.workout_completion_rate < 0.6:
        return LoadDecision.MAINTAIN, round(
            min(provisional_target_tss, completion.planned_tss), 2
        )
    return LoadDecision.MAINTAIN, round(provisional_target_tss, 2)


def _adaptation_method(completion) -> str:
    if completion.activities_with_tss > 0 and completion.tss_coverage >= 0.5:
        return POWER_TSS
    if completion.activities_with_rpe_load > 0:
        return RPE_FALLBACK
    return INSUFFICIENT_DATA


def _generate_week_for_target(
    db: Session,
    profile: CyclistProfile,
    week: PlannedWeek,
    requested_target_tss: float,
    decision: LoadDecision,
    method: str,
) -> dict:
    cyclist = Cyclist(
        cyclist_id=1,
        modalities=[Modality(profile.modality)],
        level=Level(profile.level),
        ftp=profile.ftp,
        weekly_hours=profile.weekly_hours,
        available_days=profile.available_days,
        objective=Objective(profile.objective),
        objective_date=profile.target_date,
    )
    domain_plan = generate_feasible_training_plan(
        cyclist=cyclist,
        modality=Modality(profile.modality),
        target_tss=requested_target_tss,
        reference_date=week.week_start,
    )
    domain_plan.requested_target_tss = requested_target_tss
    domain_plan.load_decision = decision
    domain_plan.aerobic_response = AerobicResponse.UNKNOWN
    domain_plan.response_prediction_method = method.lower()
    summary = build_training_plan_summary(domain_plan)
    week.requested_target_tss = summary["requested_target_tss"]
    week.adapted_target_tss = summary["target_tss"]
    week.estimated_total_tss = summary["estimated_total_tss"]
    week.expected_aerobic_decoupling = None
    week.response_prediction_method = summary["response_prediction_method"]
    week.load_decision = summary["load_decision"]
    week.generated_at = utc_now()
    week.status = "ACTIVE"
    week.workouts.clear()
    db.flush()
    for position, workout in enumerate(domain_plan.workouts, start=1):
        scheduled = week.week_start + timedelta(days=DAY_ORDER[workout.day])
        db.add(
            PlannedWorkout(
                planned_week=week,
                **_workout_data(workout, summary, position, scheduled),
            )
        )
    return summary


def _decision_reason(
    response_classification: str,
    load_decision: str | None,
    registered_tss: float,
    planned_tss: float,
    registered_rpe_load: float,
    activities_with_tss: int,
    completed_activity_count: int,
    provisional_target_tss: float | None,
    requested_target_tss: float | None,
    adapted_target_tss: float | None,
    adaptation_method: str,
    median_perceived_exertion: float | None,
    workout_completion_rate: float,
) -> str:
    response_text = {
        "ELEVATED": "La respuesta aeróbica registrada fue elevada",
        "STABLE": "La respuesta aeróbica registrada fue estable",
        "UNKNOWN": "No hubo suficientes datos de respuesta aeróbica",
    }[response_classification]
    decision_text = {
        "INCREASE": "la decisión semanal es aumentar la carga",
        "REDUCE": "la decisión semanal es reducir la carga",
        "MAINTAIN": "la decisión semanal es mantener la carga de referencia",
        None: "todavía no hay datos suficientes para una decisión semanal de carga",
    }[load_decision]
    if activities_with_tss > 0:
        load_text = (
            f"Se registraron {registered_tss:.1f} de {planned_tss:.1f} TSS planificados."
        )
    elif registered_rpe_load > 0:
        load_text = (
            f"Las {completed_activity_count} actividades realizadas no aportaron TSS; "
            f"su carga percibida fue {registered_rpe_load:.1f} unidades RPE."
        )
    elif completed_activity_count > 0:
        load_text = (
            f"Se registraron {completed_activity_count} actividades, pero no contienen "
            "TSS ni esfuerzo percibido para cuantificar su carga."
        )
    else:
        load_text = "No se registraron actividades durante la semana."
    method_text = {
        POWER_TSS: "La adaptación se calculó con potencia y TSS",
        RPE_FALLBACK: "La adaptación se calculó con cumplimiento, duración y RPE",
        INSUFFICIENT_DATA: "La carga provisional se conservó por falta de datos suficientes",
    }[adaptation_method]
    if adaptation_method == RPE_FALLBACK and median_perceived_exertion is not None:
        method_text += f" (RPE mediano {median_perceived_exertion:.1f})"
    reason = f"{response_text}; {decision_text}. {load_text} {method_text}."
    if provisional_target_tss is not None and requested_target_tss is not None:
        reason += (
            f" La previsión de temporada era {provisional_target_tss:.1f} TSS "
            f"y la revisión solicitó {requested_target_tss:.1f} TSS."
        )
        if (
            adaptation_method == RPE_FALLBACK
            and workout_completion_rate < 0.6
            and requested_target_tss < provisional_target_tss
        ):
            reason += (
                f" El incremento provisional se canceló por bajo cumplimiento "
                f"({workout_completion_rate * 100:.0f} % de las sesiones vinculadas)."
            )
    if (
        requested_target_tss is not None
        and adapted_target_tss is not None
        and abs(requested_target_tss - adapted_target_tss) > 0.01
    ):
        reason += (
            f" Las restricciones de disponibilidad dejaron un objetivo factible "
            f"de {adapted_target_tss:.1f} TSS."
        )
    return reason


def advance_plan(
    db: Session,
    user: User,
    profile: CyclistProfile,
    settings: Settings,
    reference: date | None = None,
) -> dict:
    """Close the elapsed active week and materialize the following week."""
    del settings
    plan = get_plan(db, user.id)
    if plan is None:
        raise LookupError("No hay un plan activo.")

    today = reference or date.today()
    weeks = sorted(plan.weeks, key=lambda item: item.position)
    active_week = next(
        (week for week in weeks if week.status == "PENDING_REVIEW"),
        next((week for week in weeks if week.status == "ACTIVE"), None),
    )
    latest_event = db.scalar(
        select(AdaptationEvent)
        .where(AdaptationEvent.season_plan_id == plan.id)
        .order_by(AdaptationEvent.created_at.desc())
    )

    if active_week is None:
        if latest_event is None:
            raise RuntimeError("El plan no tiene una semana activa.")
        completed = next(week for week in weeks if week.id == latest_event.source_week_id)
        return {
            "status": "COMPLETED",
            "already_processed": True,
            "completed_week": completed,
            "adaptation": latest_event,
            "active_week": None,
        }

    if today <= active_week.week_end:
        if latest_event is not None and latest_event.target_week_id == active_week.id:
            completed = next(week for week in weeks if week.id == latest_event.source_week_id)
            return {
                "status": "ALREADY_PROCESSED",
                "already_processed": True,
                "completed_week": completed,
                "adaptation": latest_event,
                "active_week": active_week,
            }
        raise ValueError("La semana activa todavía no ha terminado.")

    existing_event = db.scalar(
        select(AdaptationEvent).where(AdaptationEvent.source_week_id == active_week.id)
    )
    if existing_event is not None:
        target = next(
            (week for week in weeks if week.id == existing_event.target_week_id),
            None,
        )
        return {
            "status": "ALREADY_PROCESSED",
            "already_processed": True,
            "completed_week": active_week,
            "adaptation": existing_event,
            "active_week": target,
        }

    utc_start, utc_end = _utc_week_bounds(active_week, profile.timezone)
    activity_records = list(
        db.scalars(
            select(ActivityRecord).where(
                ActivityRecord.user_id == user.id,
                ActivityRecord.started_at >= utc_start,
                ActivityRecord.started_at < utc_end,
            )
        )
    )
    completion = summarize_completed_week(active_week, activity_records)
    response = classify_aerobic_response(completion.median_aerobic_decoupling).value
    next_week = next(
        (week for week in weeks if week.position == active_week.position + 1),
        None,
    )
    provisional_target = next_week.provisional_target_tss if next_week is not None else None
    method = _adaptation_method(completion)
    generated_summary = None
    if next_week is not None:
        if method == POWER_TSS:
            generated_summary = _generate_week(db, user, profile, next_week)
        else:
            decision = LoadDecision.MAINTAIN
            target = float(provisional_target)
            if method == RPE_FALLBACK:
                decision, target = _rpe_adaptation(completion, target)
            generated_summary = _generate_week_for_target(
                db, profile, next_week, target, decision, method
            )
    load_decision = generated_summary["load_decision"] if generated_summary else None
    adapted_target = generated_summary["target_tss"] if generated_summary else None
    reason = _decision_reason(
        response,
        load_decision,
        completion.registered_tss,
        completion.planned_tss,
        completion.registered_rpe_load,
        completion.activities_with_tss,
        completion.completed_activity_count,
        provisional_target,
        generated_summary["requested_target_tss"] if generated_summary else None,
        adapted_target,
        method,
        completion.median_perceived_exertion,
        completion.workout_completion_rate,
    )

    review = WeeklyReview(
        planned_week=active_week,
        planned_tss=completion.planned_tss,
        registered_tss=completion.registered_tss,
        tss_coverage=completion.tss_coverage,
        planned_duration_minutes=completion.planned_duration_minutes,
        registered_duration_minutes=completion.registered_duration_minutes,
        planned_workout_count=completion.planned_workout_count,
        completed_workout_count=completion.linked_workout_count,
        activity_count=completion.completed_activity_count,
        activities_with_tss=completion.activities_with_tss,
        activities_without_tss=completion.activities_without_tss,
        registered_rpe_load=completion.registered_rpe_load,
        median_perceived_exertion=completion.median_perceived_exertion,
        activities_with_rpe_load=completion.activities_with_rpe_load,
        activities_without_load=completion.activities_without_load,
        response_median=completion.median_aerobic_decoupling,
        response_count=completion.responses_available,
        load_decision=load_decision,
        adaptation_method=method,
        decision_reason=reason,
        closed_at=utc_now(),
    )
    event = AdaptationEvent(
        season_plan_id=plan.id,
        source_week_id=active_week.id,
        target_week_id=next_week.id if next_week else None,
        previous_target_tss=completion.planned_tss,
        provisional_target_tss=provisional_target,
        adapted_target_tss=adapted_target,
        load_decision=load_decision,
        observed_aerobic_decoupling=completion.median_aerobic_decoupling,
        response_classification=response,
        adaptation_method=method,
        reason=reason,
        rule_version=ADAPTATION_RULE_VERSION,
    )
    active_week.status = "COMPLETED"
    active_week.completed_at = utc_now()
    if next_week is None:
        plan.status = "COMPLETED"
    db.add_all([review, event])
    db.commit()

    refreshed = get_plan(db, user.id, plan.id)
    refreshed_weeks = sorted(refreshed.weeks, key=lambda item: item.position)
    completed = next(week for week in refreshed_weeks if week.id == active_week.id)
    target = next(
        (week for week in refreshed_weeks if next_week is not None and week.id == next_week.id),
        None,
    )
    db.refresh(event)
    return {
        "status": "ADVANCED" if target is not None else "COMPLETED",
        "already_processed": False,
        "completed_week": completed,
        "adaptation": event,
        "active_week": target,
    }


def recalculate_week_review(
    db: Session,
    user_id: UUID,
    profile: CyclistProfile,
    week_id: UUID,
) -> WeeklyReview:
    """Refresh observed metrics after a completed week's activities change."""
    plan = get_plan(db, user_id)
    if plan is None:
        raise LookupError("No hay un plan activo.")
    week = next((item for item in plan.weeks if item.id == week_id), None)
    if week is None:
        raise LookupError("Semana no encontrada.")
    if week.status != "COMPLETED" or week.review is None:
        raise ValueError("Sólo se pueden recalcular semanas cerradas.")

    utc_start, utc_end = _utc_week_bounds(week, profile.timezone)
    activities = list(
        db.scalars(
            select(ActivityRecord).where(
                ActivityRecord.user_id == user_id,
                ActivityRecord.started_at >= utc_start,
                ActivityRecord.started_at < utc_end,
            )
        )
    )
    completion = summarize_completed_week(week, activities)
    review = week.review
    review.planned_tss = completion.planned_tss
    review.registered_tss = completion.registered_tss
    review.tss_coverage = completion.tss_coverage
    review.planned_duration_minutes = completion.planned_duration_minutes
    review.registered_duration_minutes = completion.registered_duration_minutes
    review.planned_workout_count = completion.planned_workout_count
    review.completed_workout_count = completion.linked_workout_count
    review.activity_count = completion.completed_activity_count
    review.activities_with_tss = completion.activities_with_tss
    review.activities_without_tss = completion.activities_without_tss
    review.registered_rpe_load = completion.registered_rpe_load
    review.median_perceived_exertion = completion.median_perceived_exertion
    review.activities_with_rpe_load = completion.activities_with_rpe_load
    review.activities_without_load = completion.activities_without_load
    review.response_median = completion.median_aerobic_decoupling
    review.response_count = completion.responses_available
    db.commit()
    db.refresh(review)
    return review
