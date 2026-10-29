import { useEffect, useState } from "react";
import { useSearchParams } from "react-router-dom";
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
import { useIntegrations } from "../hooks/useIntegrations";
import type { AuthenticatedUser } from "../api/types";
import { IntegrationLogo } from "../components/IntegrationLogo";

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

const connectionMessages: Record<string, string> = {
  "strava-cancelled": "No se ha conectado Strava porque cancelaste la autorización.",
  "strava-invalid-state": "La solicitud de conexión ha caducado. Vuelve a intentarlo.",
  "strava-error": "No se ha podido completar la conexión con Strava. Vuelve a intentarlo.",
};

export function ProfilePage({ user, onSaved }: { user: AuthenticatedUser | null; onSaved?: () => void }) {
  const [saved, setSaved] = useState(false);
  const [saveError, setSaveError] = useState<string | null>(null);
  const [connectionBusy, setConnectionBusy] = useState(false);
  const [connectionError, setConnectionError] = useState<string | null>(null);
  const [searchParams] = useSearchParams();
  const { profile, loading, error: profileError, save } = useCyclistProfile();
  const integrations = useIntegrations();
  const connectionMessage = connectionMessages[searchParams.get("connection") ?? ""];

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

        <section className="profile-form__section profile-connections" id="connections">
          <header>
            <h2>Aplicaciones conectadas</h2>
            <p>Conecta tus plataformas deportivas para incorporar actividades sin introducirlas manualmente.</p>
          </header>

          {connectionMessage && (
            <p className="profile-connections__notice" role="status">{connectionMessage}</p>
          )}
          {(connectionError || integrations.error) && (
            <p className="profile-connections__error" role="alert">
              {connectionError ?? integrations.error}
            </p>
          )}

          <article className="profile-connections__card">
            <IntegrationLogo provider="STRAVA" className="profile-connections__logo" />
            <div className="profile-connections__content">
              <div className="profile-connections__title">
                <h3>Strava</h3>
                {integrations.strava?.connected && <span>Conectado</span>}
              </div>

              {integrations.loading ? (
                <p role="status">Comprobando conexión…</p>
              ) : integrations.strava?.connected ? (
                <div className="profile-connections__connected-summary">
                  <p>
                    <strong>{integrations.strava.external_display_name || "Atleta de Strava"}</strong>
                    {integrations.strava.connected_at && (
                      <>
                        <span aria-hidden="true"> · </span>
                        <time dateTime={integrations.strava.connected_at}>
                        Conectada desde el {new Date(integrations.strava.connected_at).toLocaleDateString("es-ES")}
                        </time>
                      </>
                    )}
                  </p>
                  {integrations.strava.sync_enabled ? (
                    <small>
                      Sincronización configurada desde {integrations.strava.sync_start_date
                        ? new Date(`${integrations.strava.sync_start_date}T00:00:00`).toLocaleDateString("es-ES")
                        : "la fecha configurada"} · {integrations.strava.sync_imported} actividades importadas
                      {integrations.strava.last_sync_at
                        ? ` · Última sincronización ${new Date(integrations.strava.last_sync_at).toLocaleString("es-ES")}`
                        : ""}
                    </small>
                  ) : (
                    <small>Configura en Actividades desde qué fecha quieres sincronizar tu historial.</small>
                  )}
                </div>
              ) : user?.is_demo ? (
                <p>Las conexiones externas no están disponibles en el modo demostración. Accede con tu cuenta para conectar Strava.</p>
              ) : !integrations.strava?.configured ? (
                <p>La integración está preparada, pero faltan las credenciales de Strava en la configuración del servidor.</p>
              ) : (
                <p>
                  Sincroniza tus actividades de ciclismo para revisarlas e incorporarlas a Veloform.
                  Nada se importará sin tu confirmación.
                </p>
              )}
              {!integrations.strava?.connected && !user?.is_demo && integrations.strava?.configured && (
                <small>Después de conectar tu cuenta podrás elegir desde qué fecha sincronizar el historial.</small>
              )}
            </div>
            <div className="profile-connections__actions">
              {integrations.strava?.connected ? (
                <button
                  className="profile-connections__disconnect"
                  type="button"
                  disabled={connectionBusy}
                  onClick={async () => {
                    if (!window.confirm("¿Desconectar Strava de Veloform? No se eliminarán las actividades que ya hayas importado.")) return;
                    setConnectionBusy(true);
                    setConnectionError(null);
                    try {
                      await integrations.disconnect();
                    } catch (cause) {
                      setConnectionError(cause instanceof Error ? cause.message : "No se ha podido desconectar Strava.");
                    } finally {
                      setConnectionBusy(false);
                    }
                  }}
                >
                  {connectionBusy ? "Desconectando…" : "Desconectar"}
                </button>
              ) : (
                <button
                  className="profile-connections__connect"
                  type="button"
                  disabled={connectionBusy || user?.is_demo || !integrations.strava?.configured}
                  onClick={async () => {
                    setConnectionBusy(true);
                    setConnectionError(null);
                    try {
                      await integrations.connect();
                    } catch (cause) {
                      setConnectionError(cause instanceof Error ? cause.message : "No se ha podido iniciar la conexión con Strava.");
                      setConnectionBusy(false);
                    }
                  }}
                >
                  {connectionBusy ? "Conectando…" : "Conectar"}
                </button>
              )}
            </div>
          </article>
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
