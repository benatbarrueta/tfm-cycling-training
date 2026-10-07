import { useEffect, useState } from "react";
import { zodResolver } from "@hookform/resolvers/zod";
import { useForm } from "react-hook-form";
import {
  cyclistSchema,
  levelOptions,
  modalityOptions,
  objectiveOptions,
  weekDayOptions,
  type CyclistFormInput,
  type CyclistFormValues,
} from "../schemas/cyclistSchema";
import "../styles/ProfilePage.css";
import { useCyclistProfile } from "../hooks/useCyclistProfile";

const modalityLabels = {
  ROAD: "Carretera",
  XCO: "Cross-country olímpico",
  XCM: "Cross-country maratón",
} as const;

const levelLabels = {
  BEGINNER: "Principiante",
  INTERMEDIATE: "Intermedio",
  ADVANCED: "Avanzado",
} as const;

const objectiveLabels = {
  ENDURANCE: "Mejorar resistencia",
  PERFORMANCE: "Mejorar rendimiento",
  RACE: "Preparar una competición",
} as const;

const weekDayLabels = {
  MONDAY: "Lunes",
  TUESDAY: "Martes",
  WEDNESDAY: "Miércoles",
  THURSDAY: "Jueves",
  FRIDAY: "Viernes",
  SATURDAY: "Sábado",
  SUNDAY: "Domingo",
} as const;

function defaultProfile(): CyclistFormValues {
  const defaultProfile: CyclistFormValues = {
    ftp: 250,
    weekly_hours: 8,
    modality: "XCO",
    level: "INTERMEDIATE",
    objective: "PERFORMANCE",
    objective_date: null,
    available_days: [
      "TUESDAY",
      "WEDNESDAY",
      "FRIDAY",
      "SUNDAY",
    ],
  };

  return defaultProfile;
}

export function ProfilePage({ onSaved }: { onSaved?: () => void } = {}) {
  const [saved, setSaved] = useState(false);
  const [saveError, setSaveError] = useState<string | null>(null);
  const { profile, loading, error: profileError, save } = useCyclistProfile();

  const {
    register,
    handleSubmit,
    reset,
    formState: {
      errors,
      isSubmitting,
    },
  } = useForm<
    CyclistFormInput,
    unknown,
    CyclistFormValues
  >({
    resolver: zodResolver(cyclistSchema),
    defaultValues: defaultProfile(),
  });

  useEffect(() => {
    if (profile) {
      reset({
        ftp: profile.ftp,
        weekly_hours: profile.weekly_hours,
        modality: profile.modality,
        level: profile.level,
        objective: profile.objective,
        objective_date: profile.target_date,
        available_days: profile.available_days,
      });
    }
  }, [profile, reset]);

  async function saveProfile(
    values: CyclistFormValues,
  ) {
    try {
      await save(values);
      setSaved(true);
      setSaveError(null);
      onSaved?.();
    } catch (cause) {
      setSaved(false);
      setSaveError(cause instanceof Error ? cause.message : "No se ha podido guardar el perfil.");
    }
  }

  if (loading) {
    return <main className="profile-page"><p role="status">Cargando perfil…</p></main>;
  }

  return (
    <main className="profile-page">
      <header className="profile-page__header">
        <p className="profile-page__eyebrow">
          Configuración
        </p>

        <h1>Perfil ciclista</h1>

        <p>
          Estos datos se utilizarán para adaptar la carga
          y generar las sesiones de entrenamiento.
        </p>
      </header>

      <form
        className="profile-form"
        onSubmit={handleSubmit(saveProfile)}
        onChange={() => setSaved(false)}
      >
        <section className="profile-form__section">
          <header>
            <h2>Capacidad y disponibilidad</h2>
            <p>
              Introduce tus valores actuales.
            </p>
          </header>

          <div className="profile-form__grid">
            <label className="profile-form__field">
              <span>FTP actual (W)</span>

              <input
                type="number"
                min="1"
                max="600"
                {...register("ftp")}
              />

              {errors.ftp?.message && (
                <small>
                  {errors.ftp.message}
                </small>
              )}
            </label>

            <label className="profile-form__field">
              <span>Horas semanales</span>

              <input
                type="number"
                min="1"
                max="40"
                step="0.5"
                {...register("weekly_hours")}
              />

              {errors.weekly_hours?.message && (
                <small>
                  {errors.weekly_hours.message}
                </small>
              )}
            </label>
          </div>
        </section>

        <section className="profile-form__section">
          <header>
            <h2>Tipo de ciclista</h2>
            <p>
              Define tu modalidad, nivel y objetivo.
            </p>
          </header>

          <div className="profile-form__grid">
            <label className="profile-form__field">
              <span>Modalidad</span>

              <select {...register("modality")}>
                {modalityOptions.map((option) => (
                  <option
                    key={option}
                    value={option}
                  >
                    {modalityLabels[option]}
                  </option>
                ))}
              </select>
            </label>

            <label className="profile-form__field">
              <span>Nivel</span>

              <select {...register("level")}>
                {levelOptions.map((option) => (
                  <option
                    key={option}
                    value={option}
                  >
                    {levelLabels[option]}
                  </option>
                ))}
              </select>
            </label>

            <label className="profile-form__field">
              <span>Objetivo</span>

              <select {...register("objective")}>
                {objectiveOptions.map((option) => (
                  <option
                    key={option}
                    value={option}
                  >
                    {objectiveLabels[option]}
                  </option>
                ))}
              </select>
            </label>

            <label className="profile-form__field">
              <span>Fecha del objetivo</span>

              <input
                type="date"
                {...register("objective_date")}
              />
            </label>
          </div>
        </section>

        <section className="profile-form__section">
          <header>
            <h2>Días disponibles</h2>
            <p>
              Selecciona los días en los que puedes
              entrenar normalmente.
            </p>
          </header>

          <div className="profile-form__days">
            {weekDayOptions.map((day) => (
              <label key={day}>
                <input
                  type="checkbox"
                  value={day}
                  {...register("available_days")}
                />

                <span>
                  {weekDayLabels[day]}
                </span>
              </label>
            ))}
          </div>

          {errors.available_days?.message && (
            <small className="profile-form__error">
              {errors.available_days.message}
            </small>
          )}
        </section>

        <footer className="profile-form__footer">
          <p role={profileError || saveError ? "alert" : undefined}>
            {saved
              ? "Perfil guardado correctamente."
              : saveError ?? profileError ?? "Los cambios se guardarán en tu cuenta."}
          </p>

          <button
            type="submit"
            disabled={isSubmitting}
          >
            Guardar perfil
          </button>
        </footer>
      </form>
    </main>
  );
}