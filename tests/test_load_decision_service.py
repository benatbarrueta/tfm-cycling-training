from app.models.load_decision import LoadDecision
from app.models.training_state import (
    LoadTrend,
    TrainingState,
)
from app.services.load_decision_service import (
    calculate_load_change_percentage,
    decide_next_load,
    calculate_target_tss,
)


def test_calculate_load_change_percentage():
    result = calculate_load_change_percentage(
        current_tss=360,
        previous_tss=300,
    )

    assert result == 20


def test_decide_reduce_load():
    state = TrainingState(
        weekly_tss=360,
        previous_week_tss=300,
        load_trend=LoadTrend.INCREASING,
        training_frequency=4,
    )

    result = decide_next_load(state)

    assert result == LoadDecision.REDUCE


def test_decide_maintain_load():
    state = TrainingState(
        weekly_tss=310,
        previous_week_tss=300,
        load_trend=LoadTrend.INCREASING,
        training_frequency=4,
    )

    result = decide_next_load(state)

    assert result == LoadDecision.MAINTAIN


def test_decide_increase_load():
    state = TrainingState(
        weekly_tss=250,
        previous_week_tss=300,
        load_trend=LoadTrend.DECREASING,
        training_frequency=3,
    )

    result = decide_next_load(state)

    assert result == LoadDecision.INCREASE

def test_calculate_target_tss_reduce():
    result = calculate_target_tss(
        current_tss=300,
        decision=LoadDecision.REDUCE,
    )

    assert result == 255


def test_calculate_target_tss_maintain():
    result = calculate_target_tss(
        current_tss=300,
        decision=LoadDecision.MAINTAIN,
    )

    assert result == 300


def test_calculate_target_tss_increase():
    result = calculate_target_tss(
        current_tss=300,
        decision=LoadDecision.INCREASE,
    )

    assert result == 315