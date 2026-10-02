from datetime import date

from app.models.activity import Activity
from app.models.cyclist import Cyclist, Modality
from app.models.training_plan import TrainingPlan

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
    estimate_aerobic_response_from_activities,
)


def generate_personalized_training_plan(
    cyclist: Cyclist,
    modality: Modality,
    activities: list[Activity],
    reference_date: date,
) -> TrainingPlan:
    """
    Generate a personalized training plan for a cyclist based on their activities and training state.

    Args:
        cyclist (Cyclist): The cyclist for whom to generate the training plan.
        modality (Modality): The modality of the training plan.
        activities (list[Activity]): The list of activities to consider.
        reference_date (date): The date to use as a reference for the training plan.

    Returns:
        TrainingPlan: The generated personalized training plan.

    Raises:
        ValueError: If a personalized training plan cannot be generated.
    """
    if has_sufficient_training_history(
        activities=activities,
        reference_date=reference_date,
    ):
        training_state = build_training_state_from_activities(
            activities=activities,
            reference_date=reference_date,
            ftp=cyclist.ftp,
        )

        aerobic_response = (
            estimate_aerobic_response_from_activities(
                activities=activities,
                reference_date=reference_date,
            )
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

    return generate_feasible_training_plan(
        cyclist=cyclist,
        modality=modality,
        target_tss=target_tss,
        reference_date=reference_date,
    )