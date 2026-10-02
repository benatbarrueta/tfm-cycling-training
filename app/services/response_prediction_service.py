import math

from datetime import date, timedelta
from statistics import median

from app.models.activity import Activity
from app.models.workout import Workout
from app.models.aerobic_response import AerobicResponse
from app.models.training_plan import TrainingPlan

from app.services.training_state_service import (
    get_or_calculate_activity_tss,
)
from app.services.aerobic_response_service import (
    classify_aerobic_response,
)

from app.data.response_model import (
    predict_response_from_artifact,
)

DAY_INDEX = {
    "MONDAY": 0,
    "TUESDAY": 1,
    "WEDNESDAY": 2,
    "THURSDAY": 3,
    "FRIDAY": 4,
    "SATURDAY": 5,
    "SUNDAY": 6,
}


def calculate_workout_date(
    reference_date: date,
    day: str,
) -> date:
    """Calcula la fecha de una sesión dentro de la semana de referencia."""
    if day not in DAY_INDEX:
        raise ValueError(
            f"Día de entrenamiento desconocido: {day}."
        )

    week_start = reference_date - timedelta(
        days=reference_date.weekday()
    )

    return week_start + timedelta(
        days=DAY_INDEX[day]
    )

def calculate_workout_intensity_factor(
    workout: Workout,
) -> float:
    """Estima el IF a partir del TSS y la duración prescritos."""
    if (
        workout.duration_minutes is None
        or workout.duration_minutes <= 0
    ):
        raise ValueError(
            "La sesión necesita una duración positiva."
        )

    if (
        workout.estimated_tss is None
        or workout.estimated_tss < 0
    ):
        raise ValueError(
            "La sesión necesita un TSS estimado válido."
        )

    duration_hours = (
        workout.duration_minutes / 60
    )

    return math.sqrt(
        workout.estimated_tss
        / (duration_hours * 100)
    )

def summarize_previous_load(
    activities: list[Activity],
    target_date: date,
    *,
    days: int,
    ftp: float,
) -> dict:
    """Resume la carga anterior a una fecha objetivo."""
    if days <= 0:
        raise ValueError(
            "El número de días debe ser positivo."
        )

    window_start = target_date - timedelta(
        days=days
    )

    previous_activities = [
        activity
        for activity in activities
        if window_start
        <= activity.date
        < target_date
    ]

    tss_values = [
        get_or_calculate_activity_tss(
            activity,
            ftp,
        )
        for activity in previous_activities
    ]

    return {
        "tss": sum(tss_values),
        "activity_count": len(previous_activities),
    }

def build_candidate_response_features(
    workout: Workout,
    session_date: date,
    activities: list[Activity],
    *,
    ftp: float,
    minimum_responses: int = 3,
) -> dict | None:
    """Construye las variables del modelo para una sesión propuesta."""
    if minimum_responses < 1:
        raise ValueError(
            "El mínimo de respuestas debe ser positivo."
        )

    if workout.estimated_tss is None:
        raise ValueError(
            "La sesión necesita un TSS estimado."
        )

    previous_responses = [
        float(activity.aerobic_decoupling)
        for activity in activities
        if activity.date < session_date
        and activity.aerobic_decoupling is not None
    ]

    if len(previous_responses) < minimum_responses:
        return None

    previous_7d = summarize_previous_load(
        activities,
        session_date,
        days=7,
        ftp=ftp,
    )

    previous_28d = summarize_previous_load(
        activities,
        session_date,
        days=28,
        ftp=ftp,
    )

    chronic_weekly_tss = (
        previous_28d["tss"] / 4
    )

    if chronic_weekly_tss <= 0:
        return None

    session_tss = float(
        workout.estimated_tss
    )

    return {
        "session_duration_minutes": float(
            workout.duration_minutes
        ),
        "session_intensity_factor": (
            calculate_workout_intensity_factor(
                workout
            )
        ),
        "session_tss": session_tss,
        "previous_7d_tss": previous_7d["tss"],
        "previous_7d_activity_count": (
            previous_7d["activity_count"]
        ),
        "previous_28d_tss": previous_28d["tss"],
        "previous_28d_activity_count": (
            previous_28d["activity_count"]
        ),
        "acute_chronic_load_ratio": (
            previous_7d["tss"]
            / chronic_weekly_tss
        ),
        "session_to_chronic_load_ratio": (
            session_tss
            / chronic_weekly_tss
        ),
        "previous_response_median": median(
            previous_responses
        ),
        "previous_response_count": len(
            previous_responses
        ),
    }

def build_planned_activity(
    workout: Workout,
    session_date: date,
    *,
    ftp: float,
) -> Activity:
    """Representa una sesión planificada para acumular su carga."""
    intensity_factor = (
        calculate_workout_intensity_factor(
            workout
        )
    )

    return Activity(
        date=session_date,
        duration_minutes=workout.duration_minutes,
        average_power=None,
        normalized_power=intensity_factor * ftp,
        intensity_factor=intensity_factor,
        tss=workout.estimated_tss,
        aerobic_decoupling=None,
    )

def predict_training_plan_responses(
    plan: TrainingPlan,
    reference_date: date,
    activities: list[Activity],
    *,
    ftp: float,
    artifact: dict,
) -> list[dict]:
    """Predice la respuesta de cada sesión de un plan candidato."""
    accumulated_activities = list(
        activities
    )

    dated_workouts = sorted(
        (
            (
                calculate_workout_date(
                    reference_date,
                    workout.day,
                ),
                workout,
            )
            for workout in plan.workouts
        ),
        key=lambda item: item[0],
    )

    results = []

    for session_date, workout in dated_workouts:
        features = build_candidate_response_features(
            workout,
            session_date,
            accumulated_activities,
            ftp=ftp,
        )

        if features is None:
            predicted_decoupling = None
            aerobic_response = AerobicResponse.UNKNOWN
        else:
            predicted_decoupling = (
                predict_response_from_artifact(
                    artifact,
                    features,
                )
            )

            aerobic_response = (
                classify_aerobic_response(
                    predicted_decoupling
                )
            )

        results.append({
            "day": workout.day,
            "session_date": session_date,
            "predicted_aerobic_decoupling": (
                predicted_decoupling
            ),
            "aerobic_response": aerobic_response,
            "features": features,
        })

        accumulated_activities.append(
            build_planned_activity(
                workout,
                session_date,
                ftp=ftp,
            )
        )

    return results

def summarize_plan_response_predictions(
    predictions: list[dict],
) -> tuple[float | None, AerobicResponse]:
    """Resume un plan usando su mayor respuesta aeróbica prevista."""
    predicted_values = [
        float(
            prediction[
                "predicted_aerobic_decoupling"
            ]
        )
        for prediction in predictions
        if prediction[
            "predicted_aerobic_decoupling"
        ] is not None
    ]

    if not predicted_values:
        return None, AerobicResponse.UNKNOWN

    expected_decoupling = max(
        predicted_values
    )

    return (
        expected_decoupling,
        classify_aerobic_response(
            expected_decoupling
        ),
    )
