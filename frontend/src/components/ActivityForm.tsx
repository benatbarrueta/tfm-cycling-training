import { zodResolver } from "@hookform/resolvers/zod";
import { useForm } from "react-hook-form";
import {
  activitySchema,
  type ActivityFormInput,
  type ActivityFormValues,
} from "../schemas/activitySchema";
import type { ActivityInput } from "../types/training";
import "../styles/ActivityForm.css";

interface ActivityFormProps {
  initialDate?: string;
  onSubmit: (activity: ActivityInput) => void;
}

export function ActivityForm({
  initialDate = "",
  onSubmit,
}: ActivityFormProps) {
  const {
    register,
    handleSubmit,
    reset,
    formState: {
      errors,
      isSubmitting,
    },
  } = useForm<
    ActivityFormInput,
    unknown,
    ActivityFormValues
  >({
    resolver: zodResolver(activitySchema),
    defaultValues: {
      date: initialDate,
      duration_minutes: "",
      average_power: "",
      normalized_power: "",
      intensity_factor: "",
      tss: "",
      aerobic_decoupling: "",
    },
  });

  function submitActivity(
  values: ActivityFormValues,
) {
  onSubmit(values);

  reset({
    date: initialDate,
    duration_minutes: "",
    average_power: "",
    normalized_power: "",
    intensity_factor: "",
    tss: "",
    aerobic_decoupling: "",
  });
}

  return (
    <form
      className="activity-form"
      onSubmit={handleSubmit(submitActivity)}
    >
      <header className="activity-form__header">
        <div>
          <p className="activity-form__eyebrow">
            Registro manual
          </p>

          <h2>Añadir actividad</h2>
        </div>

        <p>
          Introduce los datos disponibles. No todos los
          campos son obligatorios.
        </p>
      </header>

      <div className="activity-form__grid">
        <label className="activity-form__field">
          <span>Fecha</span>

          <input
            type="date"
            {...register("date")}
          />

          {errors.date?.message && (
            <small>{errors.date.message}</small>
          )}
        </label>

        <label className="activity-form__field">
          <span>Duración (minutos)</span>

          <input
            type="number"
            min="0"
            step="1"
            placeholder="90"
            {...register("duration_minutes")}
          />

          {errors.duration_minutes?.message && (
            <small>
              {errors.duration_minutes.message}
            </small>
          )}
        </label>

        <label className="activity-form__field">
          <span>Potencia media (W)</span>

          <input
            type="number"
            min="0"
            step="0.1"
            placeholder="180"
            {...register("average_power")}
          />

          {errors.average_power?.message && (
            <small>
              {errors.average_power.message}
            </small>
          )}
        </label>

        <label className="activity-form__field">
          <span>Potencia normalizada (W)</span>

          <input
            type="number"
            min="0"
            step="0.1"
            placeholder="200"
            {...register("normalized_power")}
          />

          {errors.normalized_power?.message && (
            <small>
              {errors.normalized_power.message}
            </small>
          )}
        </label>

        <label className="activity-form__field">
          <span>Factor de intensidad</span>

          <input
            type="number"
            min="0"
            max="2"
            step="0.01"
            placeholder="0.80"
            {...register("intensity_factor")}
          />

          {errors.intensity_factor?.message && (
            <small>
              {errors.intensity_factor.message}
            </small>
          )}
        </label>

        <label className="activity-form__field">
          <span>TSS</span>

          <input
            type="number"
            min="0"
            step="0.1"
            placeholder="64"
            {...register("tss")}
          />

          {errors.tss?.message && (
            <small>{errors.tss.message}</small>
          )}
        </label>

        <label className="activity-form__field">
          <span>Desacoplamiento aeróbico (%)</span>

          <input
            type="number"
            step="0.1"
            placeholder="4.5"
            {...register("aerobic_decoupling")}
          />

          {errors.aerobic_decoupling?.message && (
            <small>
              {errors.aerobic_decoupling.message}
            </small>
          )}
        </label>
      </div>

      <footer className="activity-form__actions">
        <p>
          Debes introducir el TSS o la combinación de
          duración y factor de intensidad.
        </p>

        <button
          type="submit"
          disabled={isSubmitting}
        >
          Añadir actividad
        </button>
      </footer>
    </form>
  );
}