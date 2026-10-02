from datetime import date

from app.models.activity import Activity
from app.models.cyclist import Cyclist, Modality
from app.models.training_plan import TrainingPlan
from app.models.aerobic_response import AerobicResponse

from app.services.cold_start_service import (
    calculate_initial_target_tss,
    has_sufficient_training_history,
)
from app.services.load_decision_service import (
    calculate_target_tss,
    decide_next_load,
)
from app.services.training_plan_service import (
    generate_feasible_training_plan,
)
from app.services.training_state_service import (
    build_training_state_from_activities,
)
from app.services.aerobic_response_service import (
    classify_aerobic_response,
    estimate_personal_decoupling_from_activities,
)

def generate_personalized_training_plan(
    cyclist: Cyclist,
    modality: Modality,
    activities: list[Activity],
    reference_date: date,
) -> TrainingPlan:
    """Genera un plan personalizado usando carga y respuesta aeróbica."""
    expected_decoupling = None
    aerobic_response = AerobicResponse.UNKNOWN
    load_decision = None

    if has_sufficient_training_history(
        activities=activities,
        reference_date=reference_date,
    ):
        training_state = build_training_state_from_activities(
            activities=activities,
            reference_date=reference_date,
            ftp=cyclist.ftp,
        )

        expected_decoupling = (
            estimate_personal_decoupling_from_activities(
                activities=activities,
                reference_date=reference_date,
            )
        )

        aerobic_response = classify_aerobic_response(
            expected_decoupling
        )

        load_decision = decide_next_load(
            training_state=training_state,
            aerobic_response=aerobic_response,
        )

        target_tss = calculate_target_tss(
            current_tss=training_state.weekly_tss,
            decision=load_decision,
        )
    else:
        target_tss = calculate_initial_target_tss(
            cyclist=cyclist,
        )

    requested_target_tss = target_tss

    plan = generate_feasible_training_plan(
        cyclist=cyclist,
        modality=modality,
        target_tss=target_tss,
        reference_date=reference_date,
    )

    plan.requested_target_tss = requested_target_tss

    plan.expected_aerobic_decoupling = expected_decoupling
    plan.aerobic_response = aerobic_response
    plan.load_decision = load_decision

    return plan
