from datetime import date

from app.models.activity import Activity
from app.models.aerobic_response import AerobicResponse
from app.models.cyclist import Cyclist, Modality
from app.models.training_plan import TrainingPlan
from app.services.aerobic_response_service import (
    classify_aerobic_response,
    estimate_personal_decoupling_from_activities,
)
from app.services.cold_start_service import (
    calculate_initial_target_tss,
    has_sufficient_training_history,
)
from app.services.load_decision_service import (
    calculate_target_tss,
    decide_next_load,
)
from app.services.response_prediction_service import (
    predict_training_plan_responses,
    summarize_plan_response_predictions,
)
from app.services.training_plan_service import (
    generate_feasible_training_plan,
)
from app.services.training_state_service import (
    build_training_state_from_activities,
)


def generate_personalized_training_plan(
    cyclist: Cyclist,
    modality: Modality,
    activities: list[Activity],
    reference_date: date,
    *,
    response_model_artifact: dict | None = None,
) -> TrainingPlan:
    """Genera un plan y adapta su carga según la respuesta prevista."""
    expected_decoupling = None
    aerobic_response = AerobicResponse.UNKNOWN
    load_decision = None
    response_prediction_method = "unavailable"

    if not has_sufficient_training_history(
        activities=activities,
        reference_date=reference_date,
    ):
        requested_target_tss = (
            calculate_initial_target_tss(
                cyclist=cyclist,
            )
        )

        plan = generate_feasible_training_plan(
            cyclist=cyclist,
            modality=modality,
            target_tss=requested_target_tss,
            reference_date=reference_date,
        )
    else:
        training_state = (
            build_training_state_from_activities(
                activities=activities,
                reference_date=reference_date,
                ftp=cyclist.ftp,
            )
        )

        initial_load_decision = decide_next_load(
            training_state=training_state,
        )

        initial_target_tss = calculate_target_tss(
            current_tss=training_state.weekly_tss,
            decision=initial_load_decision,
        )

        candidate_plan = (
            generate_feasible_training_plan(
                cyclist=cyclist,
                modality=modality,
                target_tss=initial_target_tss,
                reference_date=reference_date,
            )
        )

        if response_model_artifact is not None:
            predictions = (
                predict_training_plan_responses(
                    candidate_plan,
                    reference_date,
                    activities,
                    ftp=cyclist.ftp,
                    artifact=response_model_artifact,
                )
            )

            (
                expected_decoupling,
                aerobic_response,
            ) = summarize_plan_response_predictions(
                predictions
            )

            if expected_decoupling is not None:
                response_prediction_method = (
                    response_model_artifact.get(
                        "model_type",
                        "response_model",
                    )
                )

        if expected_decoupling is None:
            expected_decoupling = (
                estimate_personal_decoupling_from_activities(
                    activities=activities,
                    reference_date=reference_date,
                )
            )

            aerobic_response = (
                classify_aerobic_response(
                    expected_decoupling
                )
            )

            if expected_decoupling is not None:
                response_prediction_method = (
                    "personal_median"
                )

        load_decision = decide_next_load(
            training_state=training_state,
            aerobic_response=aerobic_response,
        )

        requested_target_tss = calculate_target_tss(
            current_tss=training_state.weekly_tss,
            decision=load_decision,
        )

        if requested_target_tss == initial_target_tss:
            plan = candidate_plan
        else:
            plan = generate_feasible_training_plan(
                cyclist=cyclist,
                modality=modality,
                target_tss=requested_target_tss,
                reference_date=reference_date,
            )

    plan.requested_target_tss = requested_target_tss
    plan.expected_aerobic_decoupling = (
        expected_decoupling
    )
    plan.aerobic_response = aerobic_response
    plan.load_decision = load_decision
    plan.response_prediction_method = (
        response_prediction_method
    )

    return plan