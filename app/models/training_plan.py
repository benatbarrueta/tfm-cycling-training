from dataclasses import dataclass

from app.models.aerobic_response import AerobicResponse
from app.models.load_decision import LoadDecision
from app.models.workout import Workout


@dataclass
class TrainingPlan:
    target_tss: float
    workouts: list[Workout]
    requested_target_tss: float | None = None
    expected_aerobic_decoupling: float | None = None
    aerobic_response: AerobicResponse = AerobicResponse.UNKNOWN
    load_decision: LoadDecision | None = None
    response_prediction_method: str = "unavailable"