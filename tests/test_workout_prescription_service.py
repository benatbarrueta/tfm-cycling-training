import pytest

from app.models.power_zone import PowerZone
from app.models.workout import Workout, WorkoutType
from app.services.workout_prescription_service import (
    calculate_duration_minutes,
    estimate_interval_workout_tss,
    estimate_segment_tss,
    generate_interval_candidates,
    prescribe_duration,
    prescribe_interval_workout,
    prescribe_power,
    select_interval_candidate,
    prescribe_continuous_workout,
    prescribe_workout,
)


def test_prescribe_vo2max_power():
    workout = Workout(
        day="TUESDAY",
        workout_type=WorkoutType.VO2MAX,
        target_tss=75,
    )

    result = prescribe_power(
        workout=workout,
        ftp=250,
    )

    assert result.target_power_min == 265
    assert result.target_power_max == 300


def test_prescribe_endurance_power():
    workout = Workout(
        day="SUNDAY",
        workout_type=WorkoutType.ENDURANCE,
        target_tss=100,
    )

    result = prescribe_power(
        workout=workout,
        ftp=250,
    )

    assert result.target_power_min == 140
    assert result.target_power_max == 187.5


def test_calculate_duration_minutes():
    result = calculate_duration_minutes(
        target_tss=64,
        intensity_factor=0.8,
    )

    assert result == 60


def test_calculate_duration_minutes_90_minutes():
    result = calculate_duration_minutes(
        target_tss=96,
        intensity_factor=0.8,
    )

    assert result == 90


def test_prescribe_duration():
    workout = Workout(
        day="SUNDAY",
        workout_type=WorkoutType.ENDURANCE,
        target_tss=96,
    )

    result = prescribe_duration(
        workout=workout,
        intensity_factor=0.8,
    )

    assert result.duration_minutes == 90


def test_estimate_segment_tss():
    result = estimate_segment_tss(
        duration_minutes=60,
        intensity_factor=0.8,
    )

    assert result == pytest.approx(64)


def test_estimate_interval_workout_tss():
    result = estimate_interval_workout_tss(
        workout_type=WorkoutType.VO2MAX,
        repetitions=4,
        work_minutes=4,
    )

    assert result > 0


def test_generate_vo2max_candidates():
    candidates = generate_interval_candidates(
        workout_type=WorkoutType.VO2MAX,
    )

    assert len(candidates) > 0

    for repetitions, work_minutes, estimated_tss in candidates:
        assert 3 <= repetitions <= 6
        assert 3 <= work_minutes <= 8
        assert estimated_tss > 0


def test_generate_threshold_candidates():
    candidates = generate_interval_candidates(
        workout_type=WorkoutType.THRESHOLD,
    )

    assert len(candidates) > 0

    for repetitions, work_minutes, estimated_tss in candidates:
        assert 2 <= repetitions <= 3
        assert 10 <= work_minutes <= 30
        assert estimated_tss > 0


def test_select_vo2max_interval_candidate():
    target_tss = 75

    repetitions, work_minutes, estimated_tss = (
        select_interval_candidate(
            workout_type=WorkoutType.VO2MAX,
            target_tss=target_tss,
        )
    )

    candidates = generate_interval_candidates(
        workout_type=WorkoutType.VO2MAX,
    )

    minimum_difference = min(
        abs(candidate[2] - target_tss)
        for candidate in candidates
    )

    assert abs(estimated_tss - target_tss) == minimum_difference
    assert 3 <= repetitions <= 6
    assert 3 <= work_minutes <= 8


def test_select_threshold_interval_candidate():
    target_tss = 70

    repetitions, work_minutes, estimated_tss = (
        select_interval_candidate(
            workout_type=WorkoutType.THRESHOLD,
            target_tss=target_tss,
        )
    )

    candidates = generate_interval_candidates(
        workout_type=WorkoutType.THRESHOLD,
    )

    minimum_difference = min(
        abs(candidate[2] - target_tss)
        for candidate in candidates
    )

    assert abs(estimated_tss - target_tss) == minimum_difference
    assert 2 <= repetitions <= 3
    assert 10 <= work_minutes <= 30


def test_prescribe_vo2max_interval_workout():
    workout = Workout(
        day="TUESDAY",
        workout_type=WorkoutType.VO2MAX,
        target_tss=75,
    )

    result = prescribe_interval_workout(
        workout=workout,
        ftp=250,
    )

    assert result.warmup is not None
    assert result.intervals is not None
    assert result.cooldown is not None

    assert result.warmup.duration_minutes == 15
    assert result.cooldown.duration_minutes == 10

    assert 3 <= result.intervals.repetitions <= 6
    assert 3 <= result.intervals.work_minutes <= 8

    assert result.intervals.work_power_min == 265
    assert result.intervals.work_power_max == 300

    assert result.intervals.recovery_power_min == 0
    assert result.intervals.recovery_power_max == 137.5

    assert result.duration_minutes > 0

    assert result.estimated_tss is not None
    assert abs(
        result.estimated_tss - result.target_tss
    ) < 15


def test_prescribe_threshold_interval_workout():
    workout = Workout(
        day="THURSDAY",
        workout_type=WorkoutType.THRESHOLD,
        target_tss=70,
    )

    result = prescribe_interval_workout(
        workout=workout,
        ftp=250,
    )

    assert result.warmup is not None
    assert result.intervals is not None
    assert result.cooldown is not None

    assert result.warmup.duration_minutes == 15
    assert result.cooldown.duration_minutes == 10

    assert 2 <= result.intervals.repetitions <= 3
    assert 10 <= result.intervals.work_minutes <= 30

    assert result.intervals.work_power_min == 227.5
    assert result.intervals.work_power_max == 262.5

    assert result.duration_minutes > 0

    assert result.estimated_tss is not None
    assert abs(
        result.estimated_tss - result.target_tss
    ) < 15

def test_vo2max_candidates_respect_total_work_limits():
    candidates = generate_interval_candidates(
        WorkoutType.VO2MAX
    )

    for repetitions, work_minutes, _ in candidates:
        total_work_minutes = repetitions * work_minutes

        assert total_work_minutes >= 12
        assert total_work_minutes <= 30

def test_threshold_candidates_respect_total_work_limits():
    candidates = generate_interval_candidates(
        WorkoutType.THRESHOLD
    )

    for repetitions, work_minutes, _ in candidates:
        total_work_minutes = repetitions * work_minutes

        assert total_work_minutes >= 20
        assert total_work_minutes <= 60

def test_prescribe_endurance_workout():
    workout = Workout(
        day="SUNDAY",
        workout_type=WorkoutType.ENDURANCE,
        target_tss=70,
    )

    result = prescribe_continuous_workout(
        workout=workout,
        ftp=250,
    )

    assert result.target_power_min == 140
    assert result.target_power_max == 187.5

    assert result.duration_minutes > 0
    assert result.estimated_tss is not None

    assert result.estimated_tss == pytest.approx(
        result.target_tss,
        abs=1,
    )

def test_prescribe_recovery_workout():
    workout = Workout(
        day="MONDAY",
        workout_type=WorkoutType.RECOVERY,
        target_tss=25,
    )

    result = prescribe_continuous_workout(
        workout=workout,
        ftp=250,
    )

    assert result.target_power_min == 0
    assert result.target_power_max == 137.5

    assert result.duration_minutes > 0
    assert result.estimated_tss is not None

def test_prescribe_tempo_workout():
    workout = Workout(
        day="SATURDAY",
        workout_type=WorkoutType.TEMPO,
        target_tss=80,
    )

    result = prescribe_continuous_workout(
        workout=workout,
        ftp=250,
    )

    assert result.target_power_min == 190
    assert result.target_power_max == 225

    assert result.duration_minutes > 0
    assert result.estimated_tss is not None

    assert result.estimated_tss == pytest.approx(
        result.target_tss,
        abs=1,
    )

def test_prescribe_workout_continuous():
    workout = Workout(
        day="SUNDAY",
        workout_type=WorkoutType.ENDURANCE,
        target_tss=70,
    )

    result = prescribe_workout(
        workout=workout,
        ftp=250,
    )

    assert result.duration_minutes is not None
    assert result.estimated_tss is not None
    assert result.target_power_min == 140
    assert result.target_power_max == 187.5


def test_prescribe_workout_interval():
    workout = Workout(
        day="TUESDAY",
        workout_type=WorkoutType.VO2MAX,
        target_tss=65,
    )

    result = prescribe_workout(
        workout=workout,
        ftp=250,
    )

    assert result.duration_minutes is not None
    assert result.estimated_tss is not None
    assert result.intervals is not None