import argparse
import json
from datetime import date, timedelta
from pathlib import Path

from app.data.activity_adapter import (
    load_goldencheetah_activities,
)
from app.data.response_model import (
    load_response_model_artifact,
)

from app.models.activity import Activity
from app.models.cyclist import Cyclist, Level, Modality
from app.models.training_objective import Objective

from app.services.training_engine_service import (
    generate_personalized_training_plan,
)
from app.services.training_plan_summary_service import (
    build_training_plan_summary,
)


def calculate_default_reference_date(
    activities: list[Activity],
) -> date:
    """Devuelve el lunes posterior a la actividad más reciente."""
    if not activities:
        raise ValueError(
            "No hay actividades para calcular la fecha de referencia."
        )

    latest_date = max(
        activity.date
        for activity in activities
    )

    days_until_next_monday = 7 - latest_date.weekday()

    return latest_date + timedelta(
        days=days_until_next_monday
    )

def main() -> None:
    """Genera un plan a partir de un JSON o ZIP de GoldenCheetah."""
    parser = argparse.ArgumentParser(
        description=(
            "Genera un plan personalizado a partir "
            "de un export de GoldenCheetah."
        )
    )

    parser.add_argument(
        "source",
        type=Path,
        help="Ruta al JSON o ZIP del atleta.",
    )
    parser.add_argument(
        "--ftp",
        type=float,
        required=True,
        help="FTP actual del ciclista en vatios.",
    )
    parser.add_argument(
        "--weekly-hours",
        type=float,
        required=True,
        help="Horas disponibles por semana.",
    )
    parser.add_argument(
        "--available-days",
        nargs="+",
        required=True,
        choices=[
            "MONDAY",
            "TUESDAY",
            "WEDNESDAY",
            "THURSDAY",
            "FRIDAY",
            "SATURDAY",
            "SUNDAY",
        ],
        help="Días disponibles para entrenar.",
    )
    parser.add_argument(
        "--modality",
        choices=[
            modality.value
            for modality in Modality
        ],
        required=True,
        help="Modalidad ciclista.",
    )
    parser.add_argument(
        "--level",
        choices=[
            level.value
            for level in Level
        ],
        required=True,
        help="Nivel del ciclista.",
    )
    parser.add_argument(
        "--objective",
        choices=[
            objective.value
            for objective in Objective
        ],
        required=True,
        help="Objetivo del entrenamiento.",
    )
    parser.add_argument(
        "--reference-date",
        type=date.fromisoformat,
        help=(
            "Fecha de referencia en formato YYYY-MM-DD. "
            "Por defecto se usa el lunes posterior "
            "a la última actividad."
        ),
    )

    parser.add_argument(
        "--response-model",
        type=Path,
        default=Path(
            "artifacts/response_balanced_linear.json"
        ),
        help=(
            "Artefacto JSON del modelo de respuesta."
        ),
    )

    args = parser.parse_args()

    activities, audit = load_goldencheetah_activities(
        args.source
    )

    if not activities:
        raise ValueError(
            "No se encontraron actividades válidas."
        )

    reference_date = (
        args.reference_date
        if args.reference_date is not None
        else calculate_default_reference_date(
            activities
        )
    )

    response_model_artifact = (
        load_response_model_artifact(
            args.response_model
        )
    )

    cyclist = Cyclist(
        cyclist_id=1,
        modalities=[
            Modality(args.modality)
        ],
        level=Level(args.level),
        ftp=args.ftp,
        weekly_hours=args.weekly_hours,
        available_days=args.available_days,
        objective=Objective(args.objective),
    )

    plan = generate_personalized_training_plan(
        cyclist=cyclist,
        modality=Modality(args.modality),
        activities=activities,
        reference_date=reference_date,
        response_model_artifact=(
            response_model_artifact
        ),
    )

    result = {
        "source_audit": audit,
        "reference_date": reference_date.isoformat(),
        "response_model": str(
            args.response_model
        ),
        "plan": build_training_plan_summary(
            plan
        ),
    }

    print(
        json.dumps(
            result,
            indent=2,
            ensure_ascii=False,
        )
    )

if __name__ == "__main__":
    main()