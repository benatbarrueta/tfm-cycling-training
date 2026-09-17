from datetime import date

from app.config.training_rules import LEVEL_RULES

from app.models.cyclist import Modality, Cyclist
from app.models.training_plan import TrainingPlan
from app.models.workout import Workout, WorkoutType

from app.services.workout_prescription_service import prescribe_workout
from app.services.training_plan_validator import validate_plan_for_level
from app.services.objective_service import get_objective_priorities


ROAD_TEMPLATES = {
    2: [
        (WorkoutType.THRESHOLD, 0.40),
        (WorkoutType.ENDURANCE, 0.60),
    ],
    3: [
        (WorkoutType.THRESHOLD, 0.30),
        (WorkoutType.ENDURANCE, 0.30),
        (WorkoutType.ENDURANCE, 0.40),
    ],
    4: [
        (WorkoutType.THRESHOLD, 0.25),
        (WorkoutType.ENDURANCE, 0.25),
        (WorkoutType.RECOVERY, 0.15),
        (WorkoutType.ENDURANCE, 0.35),
    ],
    5: [
        (WorkoutType.THRESHOLD, 0.20),
        (WorkoutType.ENDURANCE, 0.20),
        (WorkoutType.RECOVERY, 0.10),
        (WorkoutType.TEMPO, 0.20),
        (WorkoutType.ENDURANCE, 0.30),
    ],
    6: [
        (WorkoutType.THRESHOLD, 0.18),
        (WorkoutType.ENDURANCE, 0.18),
        (WorkoutType.RECOVERY, 0.10),
        (WorkoutType.TEMPO, 0.18),
        (WorkoutType.ENDURANCE, 0.16),
        (WorkoutType.ENDURANCE, 0.20),
    ],
}


XCO_TEMPLATES = {
    2: [
        (WorkoutType.VO2MAX, 0.40),
        (WorkoutType.ENDURANCE, 0.60),
    ],
    3: [
        (WorkoutType.VO2MAX, 0.30),
        (WorkoutType.ENDURANCE, 0.30),
        (WorkoutType.THRESHOLD, 0.40),
    ],
    4: [
        (WorkoutType.VO2MAX, 0.25),
        (WorkoutType.ENDURANCE, 0.25),
        (WorkoutType.THRESHOLD, 0.25),
        (WorkoutType.ENDURANCE, 0.25),
    ],
    5: [
        (WorkoutType.VO2MAX, 0.20),
        (WorkoutType.ENDURANCE, 0.20),
        (WorkoutType.RECOVERY, 0.10),
        (WorkoutType.THRESHOLD, 0.20),
        (WorkoutType.ENDURANCE, 0.30),
    ],
    6: [
        (WorkoutType.VO2MAX, 0.18),
        (WorkoutType.ENDURANCE, 0.17),
        (WorkoutType.RECOVERY, 0.10),
        (WorkoutType.THRESHOLD, 0.18),
        (WorkoutType.ENDURANCE, 0.17),
        (WorkoutType.ENDURANCE, 0.20),
    ],
}

XCM_TEMPLATES = {
    2: [
        (WorkoutType.THRESHOLD, 0.35),
        (WorkoutType.ENDURANCE, 0.65),
    ],

    3: [
        (WorkoutType.THRESHOLD, 0.25),
        (WorkoutType.ENDURANCE, 0.30),
        (WorkoutType.ENDURANCE, 0.45),
    ],

    4: [
        (WorkoutType.THRESHOLD, 0.20),
        (WorkoutType.ENDURANCE, 0.25),
        (WorkoutType.TEMPO, 0.20),
        (WorkoutType.ENDURANCE, 0.35),
    ],

    5: [
        (WorkoutType.THRESHOLD, 0.18),
        (WorkoutType.ENDURANCE, 0.18),
        (WorkoutType.RECOVERY, 0.10),
        (WorkoutType.TEMPO, 0.20),
        (WorkoutType.ENDURANCE, 0.34),
    ],

    6: [
        (WorkoutType.THRESHOLD, 0.15),
        (WorkoutType.ENDURANCE, 0.15),
        (WorkoutType.RECOVERY, 0.10),
        (WorkoutType.TEMPO, 0.15),
        (WorkoutType.ENDURANCE, 0.20),
        (WorkoutType.ENDURANCE, 0.25),
    ],
}

DAY_ORDER = {
    "MONDAY": 0,
    "TUESDAY": 1,
    "WEDNESDAY": 2,
    "THURSDAY": 3,
    "FRIDAY": 4,
    "SATURDAY": 5,
    "SUNDAY": 6,
}

INTENSE_WORKOUT_TYPES = {
    WorkoutType.THRESHOLD,
    WorkoutType.VO2MAX,
}

def generate_training_plan(
    cyclist: Cyclist,
    modality: Modality,
    target_tss: float,
) -> TrainingPlan:
    """
    Generate a training plan for a cyclist based on their available days and target TSS.
    
    Args:
        cyclist (Cyclist): The cyclist for whom to generate the training plan.
        modality (Modality): The cycling modality (e.g., ROAD, XCO, XCM).
        target_tss (float): The target Training Stress Score for the week.

    Returns:
        TrainingPlan: A training plan containing workouts for the specified days.
    
    Raises:
        ValueError: If the target TSS is not greater than 0, if the cyclist
        does not practice the specified modality, if the available days are not
        between 2 and 6, or if there are duplicate or invalid days.
    """
    if target_tss <= 0:
        raise ValueError(
            "Target TSS must be greater than 0"
        )

    if modality not in cyclist.modalities:
        raise ValueError(
            f"Cyclist does not practice modality: {modality.value}"
        )

    available_days = cyclist.available_days

    if len(available_days) < 2 or len(available_days) > 6:
        raise ValueError(
            "Available training days must be between 2 and 6"
        )

    normalized_days = [
        day.upper()
        for day in available_days
    ]

    if len(set(normalized_days)) != len(normalized_days):
        raise ValueError(
            "Available days cannot contain duplicates"
        )

    for day in normalized_days:
        if day not in DAY_ORDER:
            raise ValueError(
                f"Invalid day: {day}"
            )

    sorted_days = sorted(
        normalized_days,
        key=lambda day: DAY_ORDER[day],
    )

    if modality == Modality.XCO:
        templates = XCO_TEMPLATES

    elif modality == Modality.XCM:
        templates = XCM_TEMPLATES

    elif modality == Modality.ROAD:
        templates = ROAD_TEMPLATES

    else:
        raise ValueError(
            f"Unsupported modality: {modality.value}"
        )

    template = templates[len(sorted_days)]

    workouts = []
    accumulated_tss = 0.0

    for index, (day, session) in enumerate(
        zip(sorted_days, template)
    ):
        workout_type, percentage = session

        if index == len(template) - 1:
            workout_tss = round(
                target_tss - accumulated_tss,
                2,
            )

        else:
            workout_tss = round(
                target_tss * percentage,
                2,
            )

            accumulated_tss += workout_tss

        workouts.append(
            Workout(
                day=day,
                workout_type=workout_type,
                target_tss=workout_tss,
            )
        )

    return TrainingPlan(
        target_tss=target_tss,
        workouts=workouts,
    )

def calculate_plan_duration(
    plan: TrainingPlan,
) -> int:
    return sum(
        workout.duration_minutes or 0
        for workout in plan.workouts
    )

def prescribe_training_plan(
    plan: TrainingPlan,
    cyclist: Cyclist,
) -> TrainingPlan:
    """
    Prescribe a training plan for a cyclist.

    Args:
        plan (TrainingPlan): The training plan to prescribe.
        cyclist (Cyclist): The cyclist for whom to prescribe the training plan.

    Returns:
        TrainingPlan: The prescribed training plan.

    Raises:
        ValueError: If the prescribed training plan exceeds the cyclist's weekly availability.
    """
    for workout in plan.workouts:
        prescribe_workout(
            workout=workout,
            ftp=cyclist.ftp,
        )

    total_minutes = calculate_plan_duration(plan)

    available_minutes = cyclist.weekly_hours * 60

    if total_minutes > available_minutes:
        raise ValueError(
            "Generated training plan exceeds cyclist weekly availability"
        )

    return plan

def generate_feasible_training_plan(
    cyclist: Cyclist,
    modality: Modality,
    target_tss: float,
    reference_date: date,
    reduction_step: float = 0.05,
    min_target_tss: float = 50,
) -> TrainingPlan:
    """
    Generate a feasible training plan for a cyclist, adapting the target TSS if necessary.

    Args:
        cyclist (Cyclist): The cyclist for whom to generate the training plan.
        modality (Modality): The modality of the training plan.
        target_tss (float): The target TSS for the training plan.
        reference_date (date): The reference date for the training plan.
        reduction_step (float): The step size by which to reduce the target TSS if necessary.
        min_target_tss (float): The minimum target TSS allowed.

    Returns:
        TrainingPlan: The generated feasible training plan.

    Raises:
        ValueError: If a feasible training plan cannot be generated within the specified constraints.
    """
    current_target_tss = target_tss

    while current_target_tss >= min_target_tss:

        # 1. Generate base plan with current target TSS
        plan = generate_training_plan(
            cyclist=cyclist,
            modality=modality,
            target_tss=current_target_tss,
        )

        # 2. Adapt workouts to the cyclist's objective and race phase
        plan.workouts = adapt_workouts_to_objective(
            workouts=plan.workouts,
            cyclist=cyclist,
            reference_date=reference_date,
        )

        # 3. Adapt workouts to the cyclist's level
        plan.workouts = adapt_workouts_to_level(
            workouts=plan.workouts,
            cyclist=cyclist,
        )

        try:
            # 4. Prescribe the training plan to calculate durations and validate against cyclist's weekly availability
            plan = prescribe_training_plan(
                plan=plan,
                cyclist=cyclist,
            )

            # 5. Validate the plan against the cyclist's level
            validate_plan_for_level(
                plan=plan,
                cyclist=cyclist,
            )

            # 6. If no exceptions were raised, return the feasible plan
            return plan

        except ValueError as error:
            # If the error is not related to exceeding weekly availability, re-raise it
            if (
                "exceeds cyclist weekly availability"
                not in str(error)
            ):
                raise

        # 7. Reduce the target TSS and try again
        current_target_tss = round(
            current_target_tss * (1 - reduction_step),
            2,
        )

    raise ValueError(
        "Could not generate a training plan "
        "within cyclist weekly availability"
    )

def adapt_workouts_to_level(
    workouts: list[Workout],
    cyclist: Cyclist,
) -> list[Workout]:
    """
    Adapt the intensity of workouts in a training plan based on the cyclist's level.

    Args:
        workouts (list[Workout]): The list of workouts in the training plan.
        cyclist (Cyclist): The cyclist for whom to adapt the workouts.

    Returns:
        list[Workout]: The adapted list of workouts with adjusted intensity.

    Raises:
        ValueError: If the cyclist's level is not recognized.
    """
    rules = LEVEL_RULES[cyclist.level]

    max_intense_workouts = rules[
        "max_intense_workouts_per_week"
    ]

    intense_count = 0

    for workout in workouts:

        if workout.workout_type not in INTENSE_WORKOUT_TYPES:
            continue

        intense_count += 1

        if intense_count > max_intense_workouts:
            workout.workout_type = WorkoutType.ENDURANCE

    return workouts

def get_preferred_workout_types(
    cyclist: Cyclist,
    reference_date: date,
) -> list[WorkoutType]:
    """
    Get the preferred workout types for a cyclist based on their training objective and race phase.
    
    Args:
        cyclist (Cyclist): The cyclist for whom to get the preferred workout types.
        reference_date (date): The date from which to calculate the race phase if the objective is RACE.

    Returns:
        list[WorkoutType]: A list of preferred workout types, sorted by priority.
    """
    priorities = get_objective_priorities(
        cyclist=cyclist,
        reference_date=reference_date,
    )

    return sorted(
        priorities,
        key=lambda workout_type: priorities[workout_type],
        reverse=True,
    )

def adapt_workouts_to_objective(
    workouts: list[Workout],
    cyclist: Cyclist,
    reference_date: date,
) -> list[Workout]:
    """
    Adapt the workout types in a training plan based on the cyclist's training objective and race phase.

    Args:
        workouts (list[Workout]): The list of workouts in the training plan.
        cyclist (Cyclist): The cyclist for whom to adapt the workouts.
        reference_date (date): The date from which to calculate the race phase if the objective is RACE.

    Returns:
        list[Workout]: The adapted list of workouts with adjusted types.
    Raises:
        ValueError: If the cyclist's objective is unsupported.
    """
    priorities = get_objective_priorities(
        cyclist=cyclist,
        reference_date=reference_date,
    )

    preferred_types = get_preferred_workout_types(
        cyclist=cyclist,
        reference_date=reference_date,
    )

    replacement_index = 0

    for workout in workouts:
        current_priority = priorities[
            workout.workout_type
        ]

        # Prioridad 3, 4 o 5:
        # mantenemos la sesión original.
        if current_priority >= 3:
            continue

        # Buscamos un tipo de entrenamiento con
        # prioridad alta (4 o 5).
        valid_replacements = [
            workout_type
            for workout_type in preferred_types
            if priorities[workout_type] >= 4
        ]

        if not valid_replacements:
            continue

        replacement_type = valid_replacements[
            replacement_index % len(valid_replacements)
        ]

        workout.workout_type = replacement_type

        replacement_index += 1

    return workouts
