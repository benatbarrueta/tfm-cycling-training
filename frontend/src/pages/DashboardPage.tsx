import { useState } from "react";
import { addDays, format, parseISO } from "date-fns";
import { es } from "date-fns/locale";
import { Link } from "react-router-dom";
import { useActivities } from "../hooks/useActivities";
import { useCyclistProfile } from "../hooks/useCyclistProfile";
import { useSeasonPlan } from "../hooks/useSeasonPlan";
import { decisionLabels, responseLabels, workoutLabels } from "../lib/labels";
import {
  getCurrentDate,
  getCurrentWeekRange,
  getSimulatedDate,
  getTodayInTimeZone,
  getWeekLabel,
  getWeekTemporalState,
  setSimulatedDate,
} from "../lib/temporal";
import { summarizeWeeklyActivities } from "../lib/weeklyActivitySummary";
import { localDateToUtcIso } from "../lib/timezone";
import type { PlannedWeek } from "../api/seasonPlans";
import { getWeeklyReviewPreview, type WeeklyReviewPreview } from "../api/seasonPlans";
import "../styles/DashboardPage.css";

const TIMEZONE = "Europe/Madrid";

function chooseWeek(weeks: PlannedWeek[], today: string): PlannedWeek | null {
  return (
    weeks.find((week) => getWeekTemporalState(today, week.week_start, week.week_end) === "CURRENT") ??
    weeks.find((week) => getWeekTemporalState(today, week.week_start, week.week_end) === "UPCOMING") ??
    weeks.at(-1) ??
    null
  );
}

export function DashboardPage() {
  const { plan, status, error, refresh, advance } = useSeasonPlan();
  const [advanceStatus, setAdvanceStatus] = useState<"idle" | "loading" | "done" | "error">("idle");
  const [advanceMessage, setAdvanceMessage] = useState<string | null>(null);
  const [reviewPreview, setReviewPreview] = useState<WeeklyReviewPreview | null>(null);
  const [developmentDate, setDevelopmentDate] = useState(getSimulatedDate() ?? "");
  const { profile } = useCyclistProfile();
  const referenceDate = getCurrentDate();
  const timezone = profile?.timezone ?? TIMEZONE;
  const today = getTodayInTimeZone(referenceDate, timezone);
  const currentWeek = getCurrentWeekRange(
    referenceDate,
    timezone,
  );
  const selectedWeek = plan === null ? null : chooseWeek(plan.weeks, today);
  const overdueActiveWeek = plan?.weeks.find(
    (week) => week.status === "ACTIVE" && week.week_end < today,
  ) ?? null;
  const activityFilters = {
    start: localDateToUtcIso(currentWeek.weekStart, timezone),
    end: localDateToUtcIso(
      format(addDays(parseISO(currentWeek.weekEnd), 1), "yyyy-MM-dd"),
      timezone,
    ),
    limit: 100,
  };
  const { activities, status: activitiesStatus, refresh: refreshActivities } =
    useActivities(activityFilters, status === "ready" || status === "missing");

  if (status === "loading") return <main className="dashboard"><p>Cargando planificación...</p></main>;
  if (status === "error") {
    return <main className="dashboard"><p>{error ?? "No se ha podido cargar la planificación."}</p><button type="button" onClick={() => void refresh()}>Reintentar</button></main>;
  }
  if (plan === null) {
    return (
      <main className="dashboard dashboard--empty">
        <section className="dashboard-empty">
          <div className="dashboard-empty__content">
            <p className="dashboard__eyebrow">Perfil completado</p>
            <h1>Tu temporada empieza aquí</h1>
            <p>
              Crea tu planificación y Veloform organizará las semanas hasta tu objetivo,
              concretando los entrenamientos de la semana activa.
            </p>
            <Link className="dashboard__primary-link" to="/plan">
              Crear mi plan de temporada
            </Link>
          </div>

          <div className="dashboard-empty__visual" aria-hidden="true">
            <span>Tu próxima semana</span>
            <div><i /><strong>Resistencia</strong><small>Base aeróbica</small></div>
            <div><i /><strong>Umbral</strong><small>Trabajo específico</small></div>
            <div><i /><strong>Salida larga</strong><small>Construir consistencia</small></div>
          </div>
        </section>

        <section className="dashboard-empty__steps" aria-label="Cómo funciona Veloform">
          <article><span>01</span><strong>Generamos tu temporada</strong><p>Según tu objetivo, nivel, disponibilidad y FTP.</p></article>
          <article><span>02</span><strong>Concretamos cada semana</strong><p>Verás sesiones, duración, potencia y carga prevista.</p></article>
          <article><span>03</span><strong>Adaptamos el siguiente paso</strong><p>Tu entrenamiento realizado y tu respuesta ajustan la carga.</p></article>
        </section>
      </main>
    );
  }
  if (selectedWeek === null) {
    return <main className="dashboard"><p>No se han encontrado semanas en la planificación.</p><Link to="/plan">Revisar planificación</Link></main>;
  }

  const temporalState = getWeekTemporalState(today, selectedWeek.week_start, selectedWeek.week_end);
  const weekLabel = getWeekLabel(selectedWeek.status, temporalState);
  const activitySummary = summarizeWeeklyActivities(
    activities,
    currentWeek.weekStart,
    currentWeek.weekEnd,
    timezone,
  );
  const plannedTss = selectedWeek.adapted_target_tss ?? selectedWeek.estimated_total_tss ?? selectedWeek.provisional_target_tss;
  const plannedHours = selectedWeek.workouts.length > 0
    ? selectedWeek.workouts.reduce((total, workout) => total + (workout.duration_minutes ?? 0), 0) / 60
    : selectedWeek.provisional_hours;
  const isCurrent = temporalState === "CURRENT";
  const progressUsesTss = activitySummary.activitiesWithTss > 0;
  const progress = !isCurrent
    ? 0
    : progressUsesTss && plannedTss > 0
      ? Math.min(100, (activitySummary.knownTss / plannedTss) * 100)
      : selectedWeek.workouts.length > 0
        ? Math.min(100, (activitySummary.linkedActivityCount / selectedWeek.workouts.length) * 100)
        : plannedHours > 0
          ? Math.min(100, (activitySummary.durationMinutes / (plannedHours * 60)) * 100)
          : 0;
  const nextWorkout = selectedWeek.workouts
    .filter((workout) => workout.scheduled_date >= today)
    .sort((left, right) => left.scheduled_date.localeCompare(right.scheduled_date))[0];

  async function closeWeek() {
    setAdvanceStatus("loading");
    setAdvanceMessage(null);
    try {
      const result = await advance(getSimulatedDate());
      setAdvanceStatus("done");
      setAdvanceMessage(
        result.already_processed
          ? "La semana ya estaba revisada."
          : result.adaptation.reason,
      );
      setReviewPreview(null);
    } catch (cause) {
      setAdvanceStatus("error");
      setAdvanceMessage(cause instanceof Error ? cause.message : "No se pudo revisar la semana.");
    }
  }

  async function openWeeklyReview() {
    setAdvanceStatus("loading");
    setAdvanceMessage(null);
    try {
      setReviewPreview(await getWeeklyReviewPreview(getSimulatedDate()));
      setAdvanceStatus("idle");
    } catch (cause) {
      setAdvanceStatus("error");
      setAdvanceMessage(cause instanceof Error ? cause.message : "No se pudo preparar la revisión.");
    }
  }

  return (
    <main className="dashboard">
      {import.meta.env.DEV && (
        <section className="dashboard__development-date">
          <div>
            <strong>Fecha simulada de desarrollo</strong>
            <span>
              {getSimulatedDate() === null
                ? "Se está usando la fecha real."
                : `Veloform está funcionando como si hoy fuera ${getSimulatedDate()}.`}
            </span>
          </div>
          <label>
            <span>Simular hoy</span>
            <input
              type="date"
              value={developmentDate}
              onChange={(event) => setDevelopmentDate(event.target.value)}
            />
          </label>
          <button
            type="button"
            disabled={developmentDate === ""}
            onClick={() => {
              setSimulatedDate(developmentDate);
              window.location.reload();
            }}
          >
            Aplicar fecha
          </button>
          {getSimulatedDate() !== null && (
            <button
              type="button"
              className="dashboard__development-reset"
              onClick={() => {
                setSimulatedDate(null);
                window.location.reload();
              }}
            >
              Usar fecha real
            </button>
          )}
        </section>
      )}

      <header className="dashboard__welcome">
        <div>
          <p className="dashboard__eyebrow">{weekLabel}</p>
          <h1>Tu entrenamiento</h1>
          <p>
            {temporalState === "UPCOMING"
              ? `Tu plan comienza el ${format(parseISO(selectedWeek.week_start), "d 'de' MMMM", { locale: es })}`
              : `Semana del ${format(parseISO(selectedWeek.week_start), "d 'de' MMMM", { locale: es })} al ${format(parseISO(selectedWeek.week_end), "d 'de' MMMM", { locale: es })}`}
          </p>
          {temporalState === "UPCOMING" && (
            <p>
              Semana del{" "}
              {format(parseISO(selectedWeek.week_start), "d 'de' MMMM", { locale: es })} al{" "}
              {format(parseISO(selectedWeek.week_end), "d 'de' MMMM", { locale: es })}
            </p>
          )}
        </div>
        <Link className="dashboard__primary-link" to="/calendar">Abrir calendario</Link>
      </header>

      {overdueActiveWeek !== null && (
        <section className="dashboard__weekly-review">
          <div>
            <strong>La semana del {format(parseISO(overdueActiveWeek.week_start), "d 'de' MMMM", { locale: es })} ha terminado</strong>
            <p>Revisa las actividades registradas y prepara la siguiente semana con los datos reales.</p>
            {advanceMessage !== null && <small>{advanceMessage}</small>}
          </div>
          <button type="button" disabled={advanceStatus === "loading"} onClick={() => void openWeeklyReview()}>
            {advanceStatus === "loading" ? "Preparando…" : "Revisar semana y preparar la siguiente"}
          </button>
        </section>
      )}

      {reviewPreview !== null && (
        <div className="dashboard__review-overlay" role="presentation">
          <section className="dashboard__review-dialog" role="dialog" aria-modal="true" aria-labelledby="weekly-review-title">
            <header>
              <div>
                <span>Revisión semanal</span>
                <h2 id="weekly-review-title">
                  Del {format(parseISO(reviewPreview.week_start), "d MMM", { locale: es })} al {format(parseISO(reviewPreview.week_end), "d MMM", { locale: es })}
                </h2>
              </div>
              <button type="button" onClick={() => setReviewPreview(null)} aria-label="Cerrar">×</button>
            </header>
            <dl>
              <div><dt>Sesiones vinculadas</dt><dd>{reviewPreview.completed_workout_count} / {reviewPreview.planned_workout_count}</dd></div>
              <div><dt>Actividades registradas</dt><dd>{reviewPreview.activity_count}</dd></div>
              <div><dt>TSS registrado</dt><dd>{reviewPreview.registered_tss.toFixed(0)} / {reviewPreview.planned_tss.toFixed(0)}</dd></div>
              <div><dt>Carga estimada</dt><dd>{reviewPreview.registered_rpe_load.toFixed(0)} RPE·min</dd></div>
              <div><dt>Tiempo registrado</dt><dd>{reviewPreview.registered_duration_minutes.toFixed(0)} / {reviewPreview.planned_duration_minutes.toFixed(0)} min</dd></div>
              <div><dt>Sin datos de carga</dt><dd>{reviewPreview.activities_without_load}</dd></div>
              <div><dt>Sin respuesta aeróbica</dt><dd>{reviewPreview.activities_without_response}</dd></div>
            </dl>
            {(reviewPreview.activities_without_load > 0 || reviewPreview.activities_without_response > 0) && (
              <p className="dashboard__review-warning">
                Puedes volver al calendario para completar los datos. También puedes cerrar la semana; los datos ausentes quedarán registrados.
              </p>
            )}
            {reviewPreview.pending_overdue_weeks > 1 && (
              <p>Quedan {reviewPreview.pending_overdue_weeks} semanas vencidas y se revisarán en orden.</p>
            )}
            <footer>
              <Link
                className="dashboard__review-calendar-link"
                to={`/calendar?view=week&date=${reviewPreview.week_start}`}
              >
                Volver al calendario
              </Link>
              <button type="button" disabled={advanceStatus === "loading"} onClick={() => void closeWeek()}>
                {advanceStatus === "loading" ? "Cerrando…" : "Cerrar semana y generar la siguiente"}
              </button>
            </footer>
          </section>
        </div>
      )}

      <section className="dashboard__metrics">
        <article>
          <span>{isCurrent ? progressUsesTss ? "TSS registrado / planificado" : "Sesiones realizadas" : "TSS objetivo"}</span>
          <strong>
            {isCurrent
              ? progressUsesTss
                ? `${activitySummary.knownTss.toFixed(0)} / ${plannedTss.toFixed(0)}`
                : `${activitySummary.linkedActivityCount} / ${selectedWeek.workouts.length}`
              : plannedTss.toFixed(0)}
          </strong>
          <small>{isCurrent && !progressUsesTss ? "Progreso calculado por cumplimiento" : isCurrent ? "Solo actividades de esta semana" : "Semana de entrenamiento seleccionada"}</small>
        </article>
        <article>
          <span>Tiempo planificado</span>
          <strong>{plannedHours.toFixed(1)} h</strong>
          <small>{selectedWeek.workouts.length} sesiones detalladas</small>
        </article>
        <article>
          <span>Respuesta aeróbica</span>
          <strong>{responseLabels[selectedWeek.workouts[0]?.aerobic_response as keyof typeof responseLabels] ?? "Sin datos"}</strong>
          <small>{selectedWeek.expected_aerobic_decoupling?.toFixed(1) ?? "—"} % previsto</small>
        </article>
        <article>
          <span>Decisión de carga</span>
          <strong>{selectedWeek.load_decision ? decisionLabels[selectedWeek.load_decision as keyof typeof decisionLabels] : "Sin determinar"}</strong>
          <small>Fase: {selectedWeek.phase}</small>
        </article>
      </section>

      <section className="dashboard__content">
        <article className="dashboard__progress">
          <header>
            <div>
              <span>{isCurrent ? "Progreso semanal" : "Actividades recientes"}</span>
              {activitiesStatus === "ready" && (
                <strong>{isCurrent ? `${progress.toFixed(0)} %` : `${activitySummary.activityCount} actividades`}</strong>
              )}
            </div>
            <Link to={`/calendar?view=week&date=${currentWeek.weekStart}`}>Ver semana</Link>
          </header>
          {activitiesStatus === "loading" && <p>Cargando actividades…</p>}
          {activitiesStatus === "error" && (
            <p>
              No se pudieron cargar las actividades recientes.{" "}
              <button type="button" onClick={() => void refreshActivities()}>Reintentar</button>
            </p>
          )}
          {activitiesStatus === "empty" && <p>No has registrado actividades esta semana.</p>}
          {activitiesStatus === "ready" && (
            <>
              {isCurrent && <div className="dashboard__progress-track" role="progressbar" aria-valuenow={progress} aria-valuemin={0} aria-valuemax={100}><span style={{ width: `${progress}%` }} /></div>}
              <p>
                {activitySummary.activityCount} actividades ·{" "}
                {activitySummary.knownTss.toFixed(0)} TSS registrados ·{" "}
                {activitySummary.durationMinutes} min de entrenamiento.
                {activitySummary.estimatedRpeLoad > 0 && ` ${activitySummary.estimatedRpeLoad.toFixed(0)} RPE·min de carga estimada.`}
                {activitySummary.activitiesWithoutTss > 0 && activitySummary.activitiesWithEstimatedLoad === 0 && ` ${activitySummary.activitiesWithoutTss} actividad${activitySummary.activitiesWithoutTss === 1 ? "" : "es"} sin datos de carga.`}
                {!isCurrent && " Las actividades anteriores no se mezclan con el progreso de la próxima semana."}
              </p>
            </>
          )}
        </article>

        <article className="dashboard__next">
          <header><span>Próxima sesión</span><Link to="/plan">Ver plan</Link></header>
          {nextWorkout === undefined ? <p>No quedan sesiones planificadas esta semana.</p> : (
            <>
              <h2>{workoutLabels[ nextWorkout.workout_type as keyof typeof workoutLabels]}</h2>
              <dl>
                <div><dt>Fecha</dt><dd>{format(parseISO(nextWorkout.scheduled_date), "EEEE d 'de' MMMM", { locale: es })}</dd></div>
                <div><dt>Duración</dt><dd>{nextWorkout.duration_minutes ?? "—"} min</dd></div>
                <div><dt>TSS</dt><dd>{nextWorkout.estimated_tss?.toFixed(0) ?? nextWorkout.target_tss.toFixed(0)}</dd></div>
              </dl>
            </>
          )}
        </article>
      </section>
    </main>
  );
}
