import pytest

from datetime import date

from app.models.cyclist import Modality, Cyclist, Level, Objective
from app.models.workout import WorkoutType, Workout

from app.services.training_plan_service import (
    generate_training_plan,
    prescribe_training_plan,
    calculate_plan_duration,
    generate_feasible_training_plan,
    adapt_workouts_to_objective,
    adapt_workouts_to_level,
)
from app.services.training_plan_validator import (
    validate_plan_for_level,
)


@pytest.mark.parametrize(
    "number_of_days",
    [2, 3, 4, 5, 6],
)
def test_generate_plan_for_different_training_days(
    number_of_days,
):
    days = [
        "MONDAY",
        "TUESDAY",
        "WEDNESDAY",
        "THURSDAY",
        "FRIDAY",
        "SATURDAY",
    ][:number_of_days]

    cyclist = Cyclist(
        cyclist_id=1,
        modalities=[Modality.ROAD],
        level=Level.INTERMEDIATE,
        ftp=250,
        weekly_hours=10,
        available_days=days,
        objective=Objective.RACE,
    )

    plan = generate_training_plan(
        cyclist=cyclist,
        modality=Modality.ROAD,
        target_tss=350,
    )

    assert len(plan.workouts) == number_of_days

    total_tss = sum(
        workout.target_tss
        for workout in plan.workouts
    )

    assert total_tss == 350

def test_calculate_plan_duration():
    cyclist = Cyclist(
        cyclist_id=1,
        modalities=[Modality.XCO],
        level=Level.INTERMEDIATE,
        ftp=250,
        weekly_hours=10,
        available_days=[
            "TUESDAY",
            "WEDNESDAY",
            "FRIDAY",
            "SUNDAY",
        ],
        objective=Objective.RACE,
    )

    plan = generate_training_plan(
        cyclist=cyclist,
        modality=Modality.XCO,
        target_tss=300,
    )

    plan = prescribe_training_plan(
        plan=plan,
        cyclist=cyclist,
    )

    validate_plan_for_level(
        plan=plan,
        cyclist=cyclist,
    )

    result = calculate_plan_duration(plan)

    assert result > 0
    assert result <= 600

def test_training_plan_exceeds_weekly_availability():
    cyclist = Cyclist(
        cyclist_id=1,
        modalities=[Modality.XCO],
        level=Level.INTERMEDIATE,
        ftp=250,
        weekly_hours=2,
        available_days=[
            "TUESDAY",
            "WEDNESDAY",
            "FRIDAY",
            "SUNDAY",
        ],
        objective=Objective.RACE,
    )

    plan = generate_training_plan(
        cyclist=cyclist,
        modality=Modality.XCO,
        target_tss=300,
    )

    with pytest.raises(
        ValueError,
        match="exceeds cyclist weekly availability",
    ):
        prescribe_training_plan(
            plan=plan,
            cyclist=cyclist,
        )

def test_generate_feasible_training_plan():
    cyclist = Cyclist(
        cyclist_id=1,
        modalities=[Modality.XCO],
        level=Level.INTERMEDIATE,
        ftp=250,
        weekly_hours=5,
        available_days=[
            "TUESDAY",
            "WEDNESDAY",
            "FRIDAY",
            "SUNDAY",
        ],
        objective=Objective.RACE,
        objective_date=date(2026, 10, 10),
    )

    plan = generate_feasible_training_plan(
        cyclist=cyclist,
        modality=Modality.XCO,
        target_tss=400,
        reference_date=date(2026, 9, 16),
    )

    total_minutes = calculate_plan_duration(plan)

    assert total_minutes <= 300
    assert plan.target_tss <= 400

def test_adapt_workouts_to_endurance_objective():
    cyclist = Cyclist(
        cyclist_id=1,
        modalities=[Modality.XCO],
        level=Level.INTERMEDIATE,
        ftp=250,
        weekly_hours=8,
        available_days=[
            "TUESDAY",
            "WEDNESDAY",
            "FRIDAY",
            "SUNDAY",
        ],
        objective=Objective.ENDURANCE,
    )

    workouts = [
        Workout(
            day="TUESDAY",
            workout_type=WorkoutType.VO2MAX,
            target_tss=70,
        ),
        Workout(
            day="WEDNESDAY",
            workout_type=WorkoutType.ENDURANCE,
            target_tss=60,
        ),
        Workout(
            day="FRIDAY",
            workout_type=WorkoutType.THRESHOLD,
            target_tss=70,
        ),
        Workout(
            day="SUNDAY",
            workout_type=WorkoutType.ENDURANCE,
            target_tss=100,
        ),
    ]

    result = adapt_workouts_to_objective(
        workouts=workouts,
        cyclist=cyclist,
        reference_date=date(2026, 9, 16),
    )

    assert result[0].workout_type == WorkoutType.ENDURANCE
    assert result[1].workout_type == WorkoutType.ENDURANCE
    assert result[2].workout_type == WorkoutType.TEMPO
    assert result[3].workout_type == WorkoutType.ENDURANCE

def test_adapt_workouts_to_performance_objective():
    cyclist = Cyclist(
        cyclist_id=1,
        modalities=[Modality.XCO],
        level=Level.INTERMEDIATE,
        ftp=250,
        weekly_hours=8,
        available_days=[
            "TUESDAY",
            "WEDNESDAY",
            "FRIDAY",
            "SUNDAY",
        ],
        objective=Objective.PERFORMANCE,
    )

    workouts = [
        Workout(
            day="TUESDAY",
            workout_type=WorkoutType.VO2MAX,
            target_tss=70,
        ),
        Workout(
            day="WEDNESDAY",
            workout_type=WorkoutType.ENDURANCE,
            target_tss=60,
        ),
        Workout(
            day="FRIDAY",
            workout_type=WorkoutType.THRESHOLD,
            target_tss=70,
        ),
        Workout(
            day="SUNDAY",
            workout_type=WorkoutType.TEMPO,
            target_tss=80,
        ),
    ]

    result = adapt_workouts_to_objective(
        workouts=workouts,
        cyclist=cyclist,
        reference_date=date(2026, 9, 16),
    )

    assert result[0].workout_type == WorkoutType.VO2MAX
    assert result[1].workout_type == WorkoutType.ENDURANCE
    assert result[2].workout_type == WorkoutType.THRESHOLD
    assert result[3].workout_type == WorkoutType.TEMPO

def test_adapt_workouts_to_race_peak_objective():
    cyclist = Cyclist(
        cyclist_id=1,
        modalities=[Modality.XCO],
        level=Level.INTERMEDIATE,
        ftp=250,
        weekly_hours=8,
        available_days=[
            "TUESDAY",
            "WEDNESDAY",
            "FRIDAY",
            "SUNDAY",
        ],
        objective=Objective.RACE,
        objective_date=date(2026, 10, 10),
    )

    workouts = [
        Workout(
            day="TUESDAY",
            workout_type=WorkoutType.RECOVERY,
            target_tss=30,
        ),
        Workout(
            day="WEDNESDAY",
            workout_type=WorkoutType.ENDURANCE,
            target_tss=60,
        ),
        Workout(
            day="FRIDAY",
            workout_type=WorkoutType.THRESHOLD,
            target_tss=70,
        ),
        Workout(
            day="SUNDAY",
            workout_type=WorkoutType.VO2MAX,
            target_tss=80,
        ),
    ]

    result = adapt_workouts_to_objective(
        workouts=workouts,
        cyclist=cyclist,
        reference_date=date(2026, 9, 16),
    )

    assert result[0].workout_type in {
        WorkoutType.THRESHOLD,
        WorkoutType.VO2MAX,
    }

    assert result[1].workout_type == WorkoutType.ENDURANCE
    assert result[2].workout_type == WorkoutType.THRESHOLD
    assert result[3].workout_type == WorkoutType.VO2MAX

def test_level_limits_objective_intensity():
    cyclist = Cyclist(
        cyclist_id=1,
        modalities=[Modality.XCO],
        level=Level.BEGINNER,
        ftp=250,
        weekly_hours=8,
        available_days=[
            "TUESDAY",
            "WEDNESDAY",
            "FRIDAY",
            "SUNDAY",
        ],
        objective=Objective.RACE,
        objective_date=date(2026, 10, 10),
    )

    workouts = [
        Workout(
            day="TUESDAY",
            workout_type=WorkoutType.RECOVERY,
            target_tss=40,
        ),
        Workout(
            day="WEDNESDAY",
            workout_type=WorkoutType.VO2MAX,
            target_tss=70,
        ),
        Workout(
            day="FRIDAY",
            workout_type=WorkoutType.THRESHOLD,
            target_tss=70,
        ),
        Workout(
            day="SUNDAY",
            workout_type=WorkoutType.ENDURANCE,
            target_tss=90,
        ),
    ]

    workouts = adapt_workouts_to_objective(
        workouts=workouts,
        cyclist=cyclist,
        reference_date=date(2026, 9, 16),
    )

    workouts = adapt_workouts_to_level(
        workouts=workouts,
        cyclist=cyclist,
    )

    intense_workouts = [
        workout
        for workout in workouts
        if workout.workout_type in {
            WorkoutType.THRESHOLD,
            WorkoutType.VO2MAX,
        }
    ]

    assert len(intense_workouts) <= 1

def test_generate_complete_feasible_training_plan():
    cyclist = Cyclist(
        cyclist_id=1,
        modalities=[
            Modality.XCO,
            Modality.XCM,
        ],
        level=Level.INTERMEDIATE,
        ftp=250,
        weekly_hours=8,
        available_days=[
            "TUESDAY",
            "WEDNESDAY",
            "FRIDAY",
            "SUNDAY",
        ],
        objective=Objective.RACE,
        objective_date=date(2026, 10, 10),
    )

    plan = generate_feasible_training_plan(
        cyclist=cyclist,
        modality=Modality.XCO,
        target_tss=350,
        reference_date=date(2026, 9, 16),
    )

    assert plan is not None

    # Debe generar una sesión por cada día disponible.
    assert len(plan.workouts) == 4

    # No puede superar las horas disponibles.
    total_minutes = calculate_plan_duration(plan)

    assert total_minutes <= cyclist.weekly_hours * 60

    # Todas las sesiones deben estar prescritas.
    for workout in plan.workouts:
        assert workout.duration_minutes is not None
        assert workout.duration_minutes > 0

        assert workout.estimated_tss is not None
        assert workout.estimated_tss > 0

    # Un ciclista INTERMEDIATE no debería superar
    # el límite configurado de sesiones intensas.
    intense_workouts = [
        workout
        for workout in plan.workouts
        if workout.workout_type in {
            WorkoutType.THRESHOLD,
            WorkoutType.VO2MAX,
        }
    ]

    assert len(intense_workouts) <= 2

def test_cannot_generate_plan_for_unregistered_modality():
    cyclist = Cyclist(
        cyclist_id=1,
        modalities=[Modality.XCO],
        level=Level.INTERMEDIATE,
        ftp=250,
        weekly_hours=8,
        available_days=[
            "TUESDAY",
            "WEDNESDAY",
            "FRIDAY",
            "SUNDAY",
        ],
        objective=Objective.PERFORMANCE,
    )

    with pytest.raises(
        ValueError,
        match="does not practice modality",
    ):
        generate_feasible_training_plan(
            cyclist=cyclist,
            modality=Modality.ROAD,
            target_tss=300,
            reference_date=date(2026, 9, 16),
        )
        