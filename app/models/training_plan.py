from dataclasses import dataclass, field

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
    response_evaluated_target_tss: float | None = None
    workout_response_predictions: list[dict] = field(
        default_factory=list
    )