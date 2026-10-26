import { format, parseISO } from "date-fns";
import { es } from "date-fns/locale";
import type { Activity } from "../api/activities";
import type { PlannedWorkout } from "../api/seasonPlans";
import { workoutLabels } from "../lib/labels";
import type { WorkoutType } from "../types/training";

interface WorkoutDetailDialogProps {
  workout: PlannedWorkout;
  activity: Activity | null;
  onClose: () => void;
  onRegister: () => void;
  onEdit: (activityId: string) => void;
}

function powerRange(minimum: number | null, maximum: number | null) {
  if (minimum === null || maximum === null) return "Sin rango de potencia";
  return `${minimum.toFixed(0)}–${maximum.toFixed(0)} W`;
}

function difference(real: number, planned: number, suffix: string) {
  const value = real - planned;
  return `${value > 0 ? "+" : ""}${value.toFixed(0)} ${suffix}`;
}

export function WorkoutDetailDialog({
  workout,
  activity,
  onClose,
  onRegister,
  onEdit,
}: WorkoutDetailDialogProps) {
  const plannedTss = workout.estimated_tss ?? workout.target_tss;
  const plannedDuration = workout.duration_minutes ?? 0;
  const summaryPower = workout.target_power_min !== null && workout.target_power_max !== null
    ? powerRange(workout.target_power_min, workout.target_power_max)
    : workout.intervals !== null
      ? `Por intervalos: ${powerRange(workout.intervals.work_power_min, workout.intervals.work_power_max)}`
      : "Sin rango de potencia";

  return (
    <div className="workout-detail__overlay" role="presentation" onMouseDown={onClose}>
      <section
        className="workout-detail"
        role="dialog"
        aria-modal="true"
        aria-labelledby="workout-detail-title"
        onMouseDown={(event) => event.stopPropagation()}
      >
        <header className="workout-detail__header">
          <div>
            <span>Sesión planificada</span>
            <h2 id="workout-detail-title">
              {workoutLabels[workout.workout_type as WorkoutType]}
            </h2>
            <p>{format(parseISO(workout.scheduled_date), "EEEE d 'de' MMMM", { locale: es })}</p>
          </div>
          <button type="button" onClick={onClose} aria-label="Cerrar detalle">×</button>
        </header>

        <dl className="workout-detail__summary">
          <div><dt>Duración</dt><dd>{workout.duration_minutes ?? "—"} min</dd></div>
          <div><dt>TSS previsto</dt><dd>{plannedTss.toFixed(0)}</dd></div>
          <div><dt>Potencia objetivo</dt><dd>{summaryPower}</dd></div>
          <div><dt>Respuesta prevista</dt><dd>{workout.predicted_aerobic_decoupling?.toFixed(1) ?? "—"}%</dd></div>
        </dl>

        {(workout.warmup !== null || workout.intervals !== null || workout.cooldown !== null) && (
          <section className="workout-detail__structure">
            <h3>Estructura de la sesión</h3>
            {workout.warmup !== null && (
              <article><span>Calentamiento</span><strong>{workout.warmup.duration_minutes} min</strong><small>{powerRange(workout.warmup.target_power_min, workout.warmup.target_power_max)}</small></article>
            )}
            {workout.intervals !== null && (
              <article>
                <span>Bloque principal</span>
                <strong>{workout.intervals.repetitions} × {workout.intervals.work_minutes} min</strong>
                <small>{powerRange(workout.intervals.work_power_min, workout.intervals.work_power_max)} · recuperación {workout.intervals.recovery_minutes} min</small>
              </article>
            )}
            {workout.cooldown !== null && (
              <article><span>Vuelta a la calma</span><strong>{workout.cooldown.duration_minutes} min</strong><small>{powerRange(workout.cooldown.target_power_min, workout.cooldown.target_power_max)}</small></article>
            )}
          </section>
        )}

        {activity !== null && (
          <section className="workout-detail__completed">
            <div><span>Actividad registrada</span><strong>{activity.title}</strong></div>
            <dl>
              <div><dt>TSS</dt><dd>{activity.tss === null ? "Sin datos" : `${activity.tss.toFixed(0)} (${difference(activity.tss, plannedTss, "TSS")})`}</dd></div>
              <div><dt>Duración</dt><dd>{activity.duration_minutes.toFixed(0)} min ({difference(activity.duration_minutes, plannedDuration, "min")})</dd></div>
              <div><dt>Desacoplamiento</dt><dd>{activity.aerobic_decoupling === null ? "Sin datos" : `${activity.aerobic_decoupling.toFixed(1)}%`}</dd></div>
            </dl>
          </section>
        )}

        <footer className="workout-detail__actions">
          <button className="workout-detail__secondary" type="button" onClick={onClose}>Cerrar</button>
          {activity === null ? (
            <button className="workout-detail__primary" type="button" onClick={onRegister}>Registrar actividad realizada</button>
          ) : (
            <button className="workout-detail__primary" type="button" onClick={() => onEdit(activity.id)}>Ver o editar actividad</button>
          )}
        </footer>
      </section>
    </div>
  );
}
