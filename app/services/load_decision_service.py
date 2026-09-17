from app.models.load_decision import LoadDecision
from app.models.training_state import TrainingState


def calculate_load_change_percentage(
    current_tss: float,
    previous_tss: float,
) -> float:
    """
    Calculate the percentage change in load between the current and previous weeks.

    Args:
        current_tss (float): The total training stress score for the current week.
        previous_tss (float): The total training stress score for the previous week.

    Returns:
        float: The percentage change in load.
    """
    if previous_tss <= 0:
        return 0.0
    
    return (
        (current_tss - previous_tss)
        / previous_tss
    ) * 100


def decide_next_load(
    training_state: TrainingState,
) -> LoadDecision:
    """
    Decide the next load based on the current training state.

    Args:
        training_state (TrainingState): The current training state.

    Returns:
        LoadDecision: The decision to reduce, maintain, or increase load.
    """
    change_percentage = calculate_load_change_percentage(
            current_tss=training_state.weekly_tss,
            previous_tss=training_state.previous_week_tss,
        )
    
    if change_percentage > 15:
        return LoadDecision.REDUCE
    
    if change_percentage < -10:
        return LoadDecision.INCREASE
    
    return LoadDecision.MAINTAIN

def calculate_target_tss(
    current_tss: float,
    decision: LoadDecision,
) -> float:
    """
    Calculate the target TSS for the next week based on the current TSS and the load decision.

    Args:
        current_tss (float): The total training stress score for the current week.
        decision (LoadDecision): The decision to reduce, maintain, or increase load.

    Returns:
        float: The target TSS for the next week.
    """
    if decision == LoadDecision.REDUCE:
        return current_tss * 0.85  # Reduce by 15%
    
    if decision == LoadDecision.INCREASE:
        return current_tss * 1.05  # Increase by 10%
    
    return current_tss  # Maintain the same TSS