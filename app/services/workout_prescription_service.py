from app.config.power_zones import POWER_ZONE_PERCENTAGES
from app.config.training_rules import (
    CONTINUOUS_WORKOUT_RULES,
    INTERVAL_RULES,
)

from app.models.power_zone import PowerZone
from app.models.workout import (
    IntervalBlock,
    SessionPhase,
    Workout,
    WorkoutType,
)
from app.services.power_zone_service import (
    calculate_power_range,
    get_power_zone,
)


def prescribe_power(
    workout: Workout,
    ftp: float,
) -> Workout:
    """
    Prescribe a power range for a given workout based on the athlete's FTP.

    Args:
        workout (Workout): The workout for which to prescribe power.
        ftp (float): The athlete's Functional Threshold Power.

    Returns:
        Workout: The workout with the prescribed power range.
    """
    if ftp <= 0:
        raise ValueError("FTP must be greater than 0")

    zone = get_power_zone(workout.workout_type)

    min_power, max_power = calculate_power_range(
        ftp=ftp,
        zone=zone,
    )

    workout.target_power_min = min_power
    workout.target_power_max = max_power

    return workout

def calculate_duration_minutes(
    target_tss: float,
    intensity_factor: float,
) -> int:
    """
    Calculate the duration of a workout in minutes based on the target TSS and intensity factor.

    Args:
        target_tss (float): The target Training Stress Score for the workout.
        intensity_factor (float): The intensity factor of the workout.

    Returns:
        int: The duration of the workout in minutes.
    """

    if target_tss <= 0:
        raise ValueError("Target TSS must be greater than 0")

    if intensity_factor <= 0:
        raise ValueError("Intensity factor must be greater than 0")

    duration_hours = (
        target_tss
        / (intensity_factor ** 2 * 100)
    )

    return round(duration_hours * 60)

def prescribe_duration(
    workout: Workout,
    intensity_factor: float,
) -> Workout:
    """
    Prescribe a duration for a given workout based on the target TSS and intensity factor.

    Args:
        workout (Workout): The workout for which to prescribe duration.
        intensity_factor (float): The intensity factor of the workout.

    Returns:
        Workout: The workout with the prescribed duration.
    """
    workout.duration_minutes = calculate_duration_minutes(
        target_tss=workout.target_tss,
        intensity_factor=intensity_factor,
    )

    return workout

def prescribe_interval_workout(
    workout: Workout,
    ftp: float,
) -> Workout:
    """
    Prescribe an interval workout based on the workout type and the athlete's FTP.

    Args:
        workout (Workout): The workout for which to prescribe the interval.
        ftp (float): The athlete's Functional Threshold Power.

    Returns:
        Workout: The workout with the prescribed interval.
    """
    if workout.workout_type not in INTERVAL_RULES:
        raise ValueError(
            f"{workout.workout_type.value} is not an interval workout"
        )

    rules = INTERVAL_RULES[workout.workout_type]

    repetitions, work_minutes, estimated_tss = (
        select_interval_candidate(
            workout_type=workout.workout_type,
            target_tss=workout.target_tss,
        )
    )

    work_zone = get_power_zone(
        workout.workout_type
    )

    work_power_min, work_power_max = (
        calculate_power_range(
            ftp=ftp,
            zone=work_zone,
        )
    )

    recovery_power_min, recovery_power_max = (
        calculate_power_range(
            ftp=ftp,
            zone=PowerZone.Z1_RECOVERY,
        )
    )

    recovery_minutes = rules["recovery_minutes"]
    warmup_minutes = rules["warmup_minutes"]
    cooldown_minutes = rules["cooldown_minutes"]

    workout.warmup = SessionPhase(
        duration_minutes=warmup_minutes,
    )

    workout.intervals = IntervalBlock(
        repetitions=repetitions,
        work_minutes=work_minutes,
        recovery_minutes=recovery_minutes,
        work_power_min=work_power_min,
        work_power_max=work_power_max,
        recovery_power_min=recovery_power_min,
        recovery_power_max=recovery_power_max,
    )

    workout.cooldown = SessionPhase(
        duration_minutes=cooldown_minutes,
    )

    total_work_minutes = (
        repetitions * work_minutes
    )

    total_recovery_minutes = (
        (repetitions - 1) * recovery_minutes
    )

    workout.duration_minutes = round(
        warmup_minutes
        + total_work_minutes
        + total_recovery_minutes
        + cooldown_minutes
    )

    workout.estimated_tss = estimated_tss

    return workout

def estimate_segment_tss(
    duration_minutes: float,
    intensity_factor: float,
) -> float:
    """
    Estimate the TSS (Training Stress Score) for a given segment of a workout.

    Args:
        duration_minutes (float): The duration of the segment in minutes.
        intensity_factor (float): The intensity factor of the segment.

    Returns:
        float: The estimated TSS for the segment.
    """
    duration_hours = duration_minutes / 60

    return (
        duration_hours
        * intensity_factor ** 2
        * 100
    )

def estimate_interval_workout_tss(
    workout_type: WorkoutType,
    repetitions: int,
    work_minutes: float,
) -> float:
    """
    Estimate the TSS (Training Stress Score) for an interval workout based on the workout type, number of repetitions, and work duration.

    Args:
        workout_type (WorkoutType): The type of interval workout.
        repetitions (int): The number of repetitions in the interval workout.
        work_minutes (float): The duration of the work phase in minutes.

    Returns:
        float: The estimated TSS for the interval workout.
    """
    rules = INTERVAL_RULES[workout_type]

    zone = get_power_zone(workout_type)

    min_percentage, max_percentage = (
        POWER_ZONE_PERCENTAGES[zone]
    )

    work_if = (
        min_percentage + max_percentage
    ) / 2

    warmup_tss = estimate_segment_tss(
        rules["warmup_minutes"],
        rules["warmup_if"],
    )

    work_tss = estimate_segment_tss(
        repetitions * work_minutes,
        work_if,
    )

    recovery_tss = estimate_segment_tss(
        (repetitions - 1)
        * rules["recovery_minutes"],
        rules["recovery_if"],
    )

    cooldown_tss = estimate_segment_tss(
        rules["cooldown_minutes"],
        rules["cooldown_if"],
    )

    return round(
        warmup_tss
        + work_tss
        + recovery_tss
        + cooldown_tss,
        2,
    )

def generate_interval_candidates(
    workout_type: WorkoutType,
) -> list[tuple[int, float, float]]:
    """
    Generate a list of interval workout candidates based on the workout type.

    Args:
        workout_type (WorkoutType): The type of interval workout.
    
    Returns:
        list[tuple[int, float, float]]: A list of tuples containing the number of repetitions, work duration, and estimated TSS for each candidate.
    """
    if workout_type not in INTERVAL_RULES:
        raise ValueError(
            f"{workout_type.value} is not an interval workout"
        )

    rules = INTERVAL_RULES[workout_type]

    candidates = []

    work_minutes = rules["min_work_minutes"]

    while work_minutes <= rules["max_work_minutes"]:

        for repetitions in range(
            rules["min_repetitions"],
            rules["max_repetitions"] + 1,
        ):
            total_work_minutes = (
                repetitions * work_minutes
            )

            if total_work_minutes < rules["min_total_work_minutes"]:
                continue

            if total_work_minutes > rules["max_total_work_minutes"]:
                continue

            estimated_tss = estimate_interval_workout_tss(
                workout_type=workout_type,
                repetitions=repetitions,
                work_minutes=work_minutes,
            )

            candidates.append(
                (
                    repetitions,
                    work_minutes,
                    estimated_tss,
                )
            )

        work_minutes += rules["work_step_minutes"]

    return candidates

def select_interval_candidate(
    workout_type: WorkoutType,
    target_tss: float,
) -> tuple[int, float, float]:
    """
    Select the best interval workout candidate based on the target TSS.

    Args:
        workout_type (WorkoutType): The type of interval workout.
        target_tss (float): The target Training Stress Score for the workout.

    Returns:
        tuple[int, float, float]: A tuple containing the selected repetitions, work duration, and estimated TSS.
    """
    candidates = generate_interval_candidates(
        workout_type=workout_type,
    )

    return min(
        candidates,
        key=lambda candidate: abs(
            candidate[2] - target_tss
        ),
    )

def prescribe_continuous_workout(
    workout: Workout,
    ftp: float,
) -> Workout:
    """
    Prescribe a continuous workout based on the workout type and the athlete's FTP.1

    Args:
        workout (Workout): The workout for which to prescribe the continuous workout.
        ftp (float): The athlete's Functional Threshold Power.

    Returns:
        Workout: The workout with the prescribed continuous workout.
    """
    if workout.workout_type not in CONTINUOUS_WORKOUT_RULES:
        raise ValueError(
            f"{workout.workout_type.value} is not a continuous workout"
        )

    if ftp <= 0:
        raise ValueError("FTP must be greater than 0")

    rules = CONTINUOUS_WORKOUT_RULES[
        workout.workout_type
    ]

    intensity_factor = rules["estimated_if"]

    zone = get_power_zone(
        workout.workout_type
    )

    min_power, max_power = calculate_power_range(
        ftp=ftp,
        zone=zone,
    )

    duration_minutes = calculate_duration_minutes(
        target_tss=workout.target_tss,
        intensity_factor=intensity_factor,
    )

    workout.target_power_min = min_power
    workout.target_power_max = max_power
    workout.duration_minutes = duration_minutes

    workout.estimated_tss = round(
        estimate_segment_tss(
            duration_minutes=duration_minutes,
            intensity_factor=intensity_factor,
        ),
        2,
    )

    return workout

def prescribe_workout(
    workout: Workout,
    ftp: float,
) -> Workout:
    """
    Prescribe a workout based on the workout type and the athlete's FTP.

    Args:
        workout (Workout): The workout for which to prescribe.
        ftp (float): The athlete's Functional Threshold Power.

    Returns:
        Workout: The workout with the prescribed power range and duration.
    """
    if workout.workout_type in CONTINUOUS_WORKOUT_RULES:
        return prescribe_continuous_workout(
            workout=workout,
            ftp=ftp,
        )

    if workout.workout_type in INTERVAL_RULES:
        return prescribe_interval_workout(
            workout=workout,
            ftp=ftp,
        )

    raise ValueError(
        f"Unsupported workout type: {workout.workout_type.value}"
    )