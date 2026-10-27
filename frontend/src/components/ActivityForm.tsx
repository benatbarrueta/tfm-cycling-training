import { useEffect, useState } from "react";
import { zodResolver } from "@hookform/resolvers/zod";
import { useForm, useWatch } from "react-hook-form";
import { activitySchema, type ActivityFormInput, type ActivityFormValues } from "../schemas/activitySchema";
import {
  listAvailablePlannedWorkouts,
  type ActivityInput,
  type AvailablePlannedWorkout,
} from "../api/activities";
import { workoutLabels } from "../lib/labels";
import type { WorkoutType } from "../types/training";
import "../styles/ActivityForm.css";

interface ActivityFormProps {
  initialValues?: Partial<ActivityFormValues>;
  initialPlannedWorkoutId?: string | null;
  activityId?: string;
  onSubmit: (activity: ActivityInput, plannedWorkoutId: string | null) => Promise<void>;
  onCancel?: () => void;
  submitLabel?: string;
}

function toIso(value: string): string {
  return new Date(value).toISOString();
}

function valueOrNull(value: number | null): number | null {
  return value === null || Number.isNaN(value) ? null : value;
}

export function ActivityForm({ initialValues, initialPlannedWorkoutId = null, activityId, onSubmit, onCancel, submitLabel = "Guardar actividad" }: ActivityFormProps) {
  const { register, handleSubmit, control, formState: { errors, isSubmitting } } = useForm<ActivityFormInput, unknown, ActivityFormValues>({
    resolver: zodResolver(activitySchema),
    defaultValues: {
      title: initialValues?.title ?? "",
      started_at: initialValues?.started_at ?? "",
      duration_minutes: initialValues?.duration_minutes ?? "",
      distance_km: initialValues?.distance_km ?? "",
      average_power: initialValues?.average_power ?? "",
      normalized_power: initialValues?.normalized_power ?? "",
      average_heart_rate: initialValues?.average_heart_rate ?? "",
      intensity_factor: initialValues?.intensity_factor ?? "",
      tss: initialValues?.tss ?? "",
      perceived_exertion: initialValues?.perceived_exertion ?? "",
      aerobic_decoupling: initialValues?.aerobic_decoupling ?? "",
      notes: initialValues?.notes ?? "",
    },
  });
  const startedAt = useWatch({ control, name: "started_at" });
  const [workouts, setWorkouts] = useState<AvailablePlannedWorkout[]>([]);
  const [plannedWorkoutId, setPlannedWorkoutId] = useState(initialPlannedWorkoutId ?? "");
  const [workoutStatus, setWorkoutStatus] = useState<"loading" | "ready" | "error">("loading");

  useEffect(() => {
    const activityDate = typeof startedAt === "string" ? startedAt.slice(0, 10) : "";
    if (activityDate === "") return;
    let active = true;
    void listAvailablePlannedWorkouts(activityDate)
      .then((items) => {
        if (!active) return;
        setWorkouts(items);
        setWorkoutStatus("ready");
        const selectable = items.filter(
          (item) => !item.already_linked || item.linked_activity_id === activityId,
        );
        setPlannedWorkoutId((current) => {
          if (selectable.some((item) => item.id === current)) return current;
          return selectable.length === 1 ? selectable[0].id : "";
        });
      })
      .catch(() => {
        if (!active) return;
        setWorkouts([]);
        setWorkoutStatus("error");
      });
    return () => {
      active = false;
    };
  }, [activityId, startedAt]);

  async function submit(values: ActivityFormValues) {
    await onSubmit({
      title: values.title,
      started_at: toIso(values.started_at),
      sport: "CYCLING",
      duration_minutes: values.duration_minutes,
      distance_km: valueOrNull(values.distance_km),
      average_power: valueOrNull(values.average_power),
      normalized_power: valueOrNull(values.normalized_power),
      average_heart_rate: valueOrNull(values.average_heart_rate),
      intensity_factor: valueOrNull(values.intensity_factor),
      tss: valueOrNull(values.tss),
      perceived_exertion: valueOrNull(values.perceived_exertion),
      aerobic_decoupling: valueOrNull(values.aerobic_decoupling),
      notes: values.notes?.trim() || null,
    }, plannedWorkoutId || null);
  }

  const fields = [
    ["distance_km", "Distancia (km)", "number"],
    ["average_power", "Potencia media (W)", "number"],
    ["normalized_power", "Potencia normalizada (W)", "number"],
    ["average_heart_rate", "FC media (ppm)", "number"],
    ["intensity_factor", "Factor de intensidad", "number"],
    ["tss", "TSS", "number"],
    ["perceived_exertion", "Esfuerzo percibido (RPE 1–10)", "number"],
    ["aerobic_decoupling", "Desacoplamiento (%)", "number"],
  ] as const;

  return (
    <form className="activity-form" onSubmit={handleSubmit(submit)}>
      <header className="activity-form__header">
        <div><p className="activity-form__eyebrow">Registro manual</p><h2>{submitLabel}</h2></div>
        <p>Introduce solo los datos que conozcas.</p>
      </header>
      <div className="activity-form__grid">
        <label className="activity-form__field"><span>Título *</span><input {...register("title")} placeholder="Salida de resistencia" />{errors.title && <small>{errors.title.message}</small>}</label>
        <label className="activity-form__field"><span>Fecha y hora *</span><input type="datetime-local" {...register("started_at")} />{errors.started_at && <small>{errors.started_at.message}</small>}</label>
        <label className="activity-form__field activity-form__field--full">
          <span>Sesión planificada</span>
          <select value={plannedWorkoutId} onChange={(event) => setPlannedWorkoutId(event.target.value)}>
            <option value="">Actividad adicional / sin sesión</option>
            {workouts.map((workout) => {
              const occupiedByAnother = workout.already_linked && workout.linked_activity_id !== activityId;
              return (
                <option key={workout.id} value={workout.id} disabled={occupiedByAnother}>
                  {workoutLabels[workout.workout_type as WorkoutType]} · {workout.duration_minutes ?? "—"} min · {(workout.estimated_tss ?? workout.target_tss).toFixed(0)} TSS{occupiedByAnother ? " · ya vinculada" : ""}
                </option>
              );
            })}
          </select>
          {workoutStatus === "ready" && workouts.length === 0 && startedAt && (
            <small className="activity-form__hint">No hay sesiones planificadas para esta fecha. Se guardará como actividad adicional.</small>
          )}
          {workoutStatus === "error" && <small>No se han podido consultar las sesiones planificadas.</small>}
        </label>
        <label className="activity-form__field"><span>Duración (minutos) *</span><input type="number" min="0.01" step="any" {...register("duration_minutes")} />{errors.duration_minutes && <small>{errors.duration_minutes.message}</small>}</label>
        {fields.map(([name, label, type]) => (
          <label className="activity-form__field" key={name}>
            <span>{label}</span>
            <input
              type={type}
              step={name === "perceived_exertion" ? "1" : "any"}
              min={name === "aerobic_decoupling" ? undefined : name === "perceived_exertion" ? "1" : "0"}
              max={name === "perceived_exertion" ? "10" : undefined}
              {...register(name)}
            />
            {name === "perceived_exertion" && (
              <small className="activity-form__hint">
                Úsalo si no tienes TSS: 1 es muy suave y 10 es un esfuerzo máximo.
              </small>
            )}
            {errors[name] && <small>{errors[name]?.message}</small>}
          </label>
        ))}
        <label className="activity-form__field activity-form__field--full"><span>Notas</span><textarea {...register("notes")} rows={3} /></label>
      </div>
      <footer className="activity-form__actions">
        {onCancel && <button type="button" onClick={onCancel}>Cancelar</button>}
        <button type="submit" disabled={isSubmitting}>{isSubmitting ? "Guardando…" : submitLabel}</button>
      </footer>
    </form>
  );
}
