import type { TrainingPlan } from "../types/training";
import { WorkoutCard } from "./WorkoutCard";
import "../styles/WeeklyPlan.css";

interface WeeklyPlanProps {
  plan: TrainingPlan;
}

const decisionLabels = {
  INCREASE: "Aumentar carga",
  MAINTAIN: "Mantener carga",
  REDUCE: "Reducir carga",
} as const;

export function WeeklyPlan({
  plan,
}: WeeklyPlanProps) {
  return (
    <section className="weekly-plan">
      <header className="weekly-plan__header">
        <div>
          <p className="weekly-plan__eyebrow">
            Plan personalizado
          </p>

          <h1>Tu semana de entrenamiento</h1>

          <p className="weekly-plan__description">
            La carga se ha adaptado según tu historial y
            tu respuesta aeróbica prevista.
          </p>
        </div>

        <div className="weekly-plan__decision">
          <span>Decisión de carga</span>
          <strong>
            {plan.load_decision !== null
              ? decisionLabels[plan.load_decision]
              : "Sin determinar"}
          </strong>
        </div>
      </header>

      <div className="weekly-plan__summary">
        <article>
          <span>TSS objetivo</span>
          <strong>{plan.target_tss.toFixed(0)}</strong>
        </article>

        <article>
          <span>TSS planificado</span>
          <strong>
            {plan.estimated_total_tss.toFixed(0)}
          </strong>
        </article>

        <article>
          <span>Tiempo total</span>
          <strong>
            {(plan.total_duration_minutes / 60).toFixed(1)} h
          </strong>
        </article>

        <article>
          <span>Respuesta prevista</span>
          <strong>
            {plan.expected_aerobic_decoupling !== null
              ? `${plan.expected_aerobic_decoupling.toFixed(1)} %`
              : "Sin datos"}
          </strong>
        </article>
      </div>

      {plan.feasibility_adjusted && (
        <p className="weekly-plan__notice">
          El objetivo inicial se ajustó a la disponibilidad
          semanal del ciclista.
        </p>
      )}

      <div className="weekly-plan__workouts">
        {plan.workouts.map((workout) => {
          const prediction =
            plan.workout_response_predictions.find(
              (item) => item.day === workout.day,
            );

          return (
            <WorkoutCard
              key={workout.day}
              workout={workout}
              prediction={prediction}
            />
          );
        })}
      </div>
    </section>
  );
}