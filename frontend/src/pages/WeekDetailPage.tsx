import { useEffect, useState } from "react";
import { format, parseISO } from "date-fns";
import { es } from "date-fns/locale";
import { Link, Navigate, useParams } from "react-router-dom";
import { useSeasonPlan } from "../hooks/useSeasonPlan";
import { getSeasonPlan, type SeasonPlan } from "../api/seasonPlans";
import { decisionLabels, phaseLabels, responseLabels, workoutLabels } from "../lib/labels";
import "../styles/WeekDetailPage.css";

export function WeekDetailPage() {
  const { planId, weekId } = useParams();
  const { plan, status } = useSeasonPlan();
  const [loadedPlan, setLoadedPlan] = useState<SeasonPlan | null>(null);
  const [archiveStatus, setArchiveStatus] = useState<"idle" | "loading" | "loaded" | "error">("idle");

  useEffect(() => {
    if (planId === undefined || plan?.id === planId) return;
    void getSeasonPlan(planId)
      .then((result) => {
        setLoadedPlan(result);
        setArchiveStatus("loaded");
      })
      .catch(() => {
        setLoadedPlan(null);
        setArchiveStatus("error");
      });
  }, [plan, planId]);

  const needsArchivedPlan = planId !== undefined && plan?.id !== planId;
  if (status === "loading" || (needsArchivedPlan && archiveStatus !== "loaded" && archiveStatus !== "error")) {
    return <main className="week-detail"><p>Cargando semana…</p></main>;
  }
  const displayedPlan = needsArchivedPlan ? loadedPlan : plan;
  const week = displayedPlan?.weeks.find((item) => item.id === weekId);
  if (week === undefined) return <Navigate to="/plan" replace />;

  const provisional = week.provisional_target_tss;
  const adapted = week.adapted_target_tss;
  const difference = adapted === null ? null : adapted - provisional;
  const percentage = difference === null || provisional === 0 ? null : (difference / provisional) * 100;

  return (
    <main className="week-detail">
      <Link className="week-detail__back" to="/plan">← Volver a temporadas</Link>
      <header className="week-detail__header">
        <div>
          <p>{phaseLabels[week.phase as keyof typeof phaseLabels]} · {week.status}</p>
          <h1>Semana del {format(parseISO(week.week_start), "d 'de' MMMM", { locale: es })}</h1>
          <span>Hasta el {format(parseISO(week.week_end), "d 'de' MMMM 'de' yyyy", { locale: es })}</span>
        </div>
        <Link to={`/calendar?view=week&date=${week.week_start}`}>Abrir en calendario</Link>
      </header>

      <section className="week-detail__comparison">
        <article><span>Previsión de temporada</span><strong>{provisional.toFixed(0)} TSS</strong></article>
        <article><span>Objetivo tras la revisión</span><strong>{week.requested_target_tss?.toFixed(0) ?? "Pendiente"}{week.requested_target_tss === null ? "" : " TSS"}</strong></article>
        <article><span>Plan factible generado</span><strong>{adapted?.toFixed(0) ?? "Pendiente"}{adapted === null ? "" : " TSS"}</strong></article>
        <article>
          <span>Cambio</span>
          <strong>{difference === null ? "Pendiente" : `${difference >= 0 ? "+" : ""}${difference.toFixed(0)} TSS`}</strong>
          {percentage !== null && <small>{percentage >= 0 ? "+" : ""}{percentage.toFixed(1)} %</small>}
        </article>
        <article><span>Decisión</span><strong>{week.load_decision ? decisionLabels[week.load_decision as keyof typeof decisionLabels] : "Sin determinar"}</strong></article>
      </section>

      {week.review !== null && (
        <section className="week-detail__review">
          <header><h2>Resultado de la semana</h2><p>{week.review.decision_reason}</p></header>
          <dl>
            <div><dt>TSS realizado</dt><dd>{week.review.registered_tss.toFixed(0)} / {week.review.planned_tss.toFixed(0)}</dd></div>
            <div><dt>Sesiones vinculadas</dt><dd>{week.review.completed_workout_count} / {week.review.planned_workout_count}</dd></div>
            <div><dt>Actividades</dt><dd>{week.review.activity_count}</dd></div>
            <div><dt>Respuesta</dt><dd>{week.review.response_median === null ? "Sin datos" : `${week.review.response_median.toFixed(1)} %`}</dd></div>
          </dl>
        </section>
      )}

      <section className="week-detail__workouts">
        <header><h2>Sesiones</h2><span>{week.workouts.length} planificadas</span></header>
        {week.workouts.length === 0 ? <p>Las sesiones se concretarán cuando esta semana esté activa.</p> : week.workouts.map((workout) => (
          <article key={workout.id}>
            <div>
              <span>{format(parseISO(workout.scheduled_date), "EEEE d MMM", { locale: es })}</span>
              <strong>{workoutLabels[workout.workout_type as keyof typeof workoutLabels]}</strong>
            </div>
            <div><span>{workout.duration_minutes ?? "—"} min</span><span>{(workout.estimated_tss ?? workout.target_tss).toFixed(0)} TSS</span></div>
            <small>{workout.aerobic_response ? responseLabels[workout.aerobic_response as keyof typeof responseLabels] : "Respuesta sin determinar"}</small>
          </article>
        ))}
      </section>
    </main>
  );
}
