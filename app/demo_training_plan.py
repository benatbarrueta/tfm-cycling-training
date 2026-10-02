import json
from datetime import date

from app.models.activity import Activity
from app.models.cyclist import Cyclist, Level, Modality
from app.models.training_objective import Objective
from app.services.training_engine_service import (
    generate_personalized_training_plan,
)
from app.services.training_plan_summary_service import (
    build_training_plan_summary,
)


def build_demo_cyclist() -> Cyclist:
    """Construye el ciclista utilizado en la demostración."""
    return Cyclist(
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

def build_demo_activities() -> list[Activity]:
    """Construye un historial con respuesta aeróbica elevada."""
    return [
        Activity(
            date=date(2026, 9, 1),
            duration_minutes=60,
            average_power=180,
            normalized_power=200,
            tss=150,
            aerobic_decoupling=7.0,
        ),
        Activity(
            date=date(2026, 9, 3),
            duration_minutes=60,
            average_power=180,
            normalized_power=200,
            tss=150,
            aerobic_decoupling=8.0,
        ),
        Activity(
            date=date(2026, 9, 7),
            duration_minutes=60,
            average_power=180,
            normalized_power=200,
            tss=155,
            aerobic_decoupling=6.0,
        ),
        Activity(
            date=date(2026, 9, 10),
            duration_minutes=60,
            average_power=180,
            normalized_power=200,
            tss=155,
        ),
    ]

def main() -> None:
    """Genera y muestra un plan personalizado de ejemplo."""
    cyclist = build_demo_cyclist()
    activities = build_demo_activities()

    plan = generate_personalized_training_plan(
        cyclist=cyclist,
        modality=Modality.XCO,
        activities=activities,
        reference_date=date(2026, 9, 16),
    )

    summary = build_training_plan_summary(plan)

    print(
        json.dumps(
            summary,
            indent=2,
            ensure_ascii=False,
        )
    )

if __name__ == "__main__":
    main()