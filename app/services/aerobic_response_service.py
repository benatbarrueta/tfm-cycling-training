import math
from datetime import date

from statistics import median


from app.models.aerobic_response import AerobicResponse
from app.models.activity import Activity

def estimate_personal_decoupling(
    previous_decouplings: list[float],
    *,
    minimum_observations: int = 3,
) -> float | None:
    """Estima la respuesta usando la mediana histórica del ciclista."""
    if minimum_observations < 1:
        raise ValueError(
            "El mínimo de observaciones debe ser positivo."
        )

    values = [
        float(value)
        for value in previous_decouplings
    ]

    if any(not math.isfinite(value) for value in values):
        raise ValueError(
            "Los desacoplamientos deben ser valores finitos."
        )

    if len(values) < minimum_observations:
        return None

    return float(median(values))

def classify_aerobic_response(
    expected_decoupling: float | None,
) -> AerobicResponse:
    """Clasifica la respuesta aeróbica prevista."""
    if expected_decoupling is None:
        return AerobicResponse.UNKNOWN

    value = float(expected_decoupling)

    if not math.isfinite(value):
        raise ValueError(
            "El desacoplamiento esperado debe ser finito."
        )

    if value > 5:
        return AerobicResponse.ELEVATED

    return AerobicResponse.STABLE

def estimate_personal_decoupling_from_activities(
    activities: list[Activity],
    reference_date: date,
    *,
    minimum_observations: int = 3,
) -> float | None:
    """Estima el desacoplamiento usando las actividades anteriores."""
    previous_decouplings = [
        activity.aerobic_decoupling
        for activity in activities
        if activity.date < reference_date
        and activity.aerobic_decoupling is not None
    ]

    return estimate_personal_decoupling(
        previous_decouplings,
        minimum_observations=minimum_observations,
    )

def estimate_aerobic_response_from_activities(
    activities: list[Activity],
    reference_date: date,
    *,
    minimum_observations: int = 3,
) -> AerobicResponse:
    """Clasifica la respuesta estimada a partir de actividades anteriores."""
    expected_decoupling = (
        estimate_personal_decoupling_from_activities(
            activities=activities,
            reference_date=reference_date,
            minimum_observations=minimum_observations,
        )
    )

    return classify_aerobic_response(
        expected_decoupling
    )
