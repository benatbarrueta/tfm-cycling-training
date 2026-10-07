import { zodResolver } from "@hookform/resolvers/zod";
import { useForm } from "react-hook-form";
import { activitySchema, type ActivityFormInput, type ActivityFormValues } from "../schemas/activitySchema";
import type { ActivityInput } from "../api/activities";
import "../styles/ActivityForm.css";

interface ActivityFormProps {
  initialValues?: Partial<ActivityFormValues>;
  onSubmit: (activity: ActivityInput) => Promise<void>;
  onCancel?: () => void;
  submitLabel?: string;
}

function toIso(value: string): string {
  return new Date(value).toISOString();
}

function valueOrNull(value: number | null): number | null {
  return value === null || Number.isNaN(value) ? null : value;
}

export function ActivityForm({ initialValues, onSubmit, onCancel, submitLabel = "Guardar actividad" }: ActivityFormProps) {
  const { register, handleSubmit, formState: { errors, isSubmitting } } = useForm<ActivityFormInput, unknown, ActivityFormValues>({
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
      aerobic_decoupling: initialValues?.aerobic_decoupling ?? "",
      notes: initialValues?.notes ?? "",
    },
  });

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
      aerobic_decoupling: valueOrNull(values.aerobic_decoupling),
      notes: values.notes?.trim() || null,
    });
  }

  const fields = [
    ["distance_km", "Distancia (km)", "number"],
    ["average_power", "Potencia media (W)", "number"],
    ["normalized_power", "Potencia normalizada (W)", "number"],
    ["average_heart_rate", "FC media (ppm)", "number"],
    ["intensity_factor", "Factor de intensidad", "number"],
    ["tss", "TSS", "number"],
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
        <label className="activity-form__field"><span>Duración (minutos) *</span><input type="number" min="0.1" step="0.1" {...register("duration_minutes")} />{errors.duration_minutes && <small>{errors.duration_minutes.message}</small>}</label>
        {fields.map(([name, label, type]) => (
          <label className="activity-form__field" key={name}><span>{label}</span><input type={type} step="0.1" min={name === "aerobic_decoupling" ? undefined : "0"} {...register(name)} />{errors[name] && <small>{errors[name]?.message}</small>}</label>
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
