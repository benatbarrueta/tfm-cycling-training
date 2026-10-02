import type {
  Workout,
  WorkoutResponsePrediction,
} from "../types/training";

import "../styles/WorkoutCard.css";

interface WorkoutCardProps {
  workout: Workout;
  prediction?: WorkoutResponsePrediction;
}

const dayLabels = {
  MONDAY: "Lunes",
  TUESDAY: "Martes",
  WEDNESDAY: "Miércoles",
  THURSDAY: "Jueves",
  FRIDAY: "Viernes",
  SATURDAY: "Sábado",
  SUNDAY: "Domingo",
} as const;

const workoutLabels = {
  RECOVERY: "Recuperación",
  ENDURANCE: "Resistencia",
  TEMPO: "Tempo",
  THRESHOLD: "Umbral",
  VO2MAX: "VO₂ máx.",
} as const;

function formatPowerRange(
  minimum: number | null,
  maximum: number | null,
): string | null {
  if (minimum === null || maximum === null) {
    return null;
  }

  return `${minimum}–${maximum} W`;
}

export function WorkoutCard({
  workout,
  prediction,
}: WorkoutCardProps) {
  const powerRange = formatPowerRange(
    workout.target_power_min,
    workout.target_power_max,
  );

  return (
    <article className="workout-card">
      <header className="workout-card__header">
        <div>
          <p className="workout-card__day">
            {dayLabels[workout.day]}
          </p>

          <h2 className="workout-card__title">
            {workoutLabels[workout.workout_type]}
          </h2>
        </div>

        <span
          className={`workout-card__response workout-card__response--${
            prediction?.aerobic_response.toLowerCase() ?? "unknown"
          }`}
        >
          {prediction?.predicted_aerobic_decoupling.toFixed(1) ?? "—"} %
        </span>
      </header>

      <dl className="workout-card__metrics">
        <div>
          <dt>Duración</dt>
          <dd>
            {workout.duration_minutes !== null
              ? `${workout.duration_minutes} min`
              : "Sin definir"}
          </dd>
        </div>

        <div>
          <dt>TSS estimado</dt>
          <dd>
            {workout.estimated_tss !== null
              ? workout.estimated_tss.toFixed(1)
              : "Sin definir"}
          </dd>
        </div>

        <div>
          <dt>Potencia</dt>
          <dd>{powerRange ?? "Por intervalos"}</dd>
        </div>
      </dl>

      {workout.intervals !== null && (
        <section className="workout-card__intervals">
          <h3>Bloque principal</h3>

          <p>
            {workout.intervals.repetitions} ×{" "}
            {workout.intervals.work_minutes} min a{" "}
            {workout.intervals.work_power_min}–
            {workout.intervals.work_power_max} W
          </p>

          <p>
            Recuperación: {workout.intervals.recovery_minutes} min
          </p>
        </section>
      )}

      {prediction !== undefined && (
        <footer className="workout-card__footer">
          Respuesta aeróbica prevista:{" "}
          <strong>{prediction.aerobic_response}</strong>
        </footer>
      )}
    </article>
  );
}