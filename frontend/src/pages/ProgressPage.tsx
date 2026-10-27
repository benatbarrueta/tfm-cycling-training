import { useEffect, useState } from "react";
import { format, parseISO } from "date-fns";
import { es } from "date-fns/locale";
import { Link } from "react-router-dom";
import { useSeasonPlan } from "../hooks/useSeasonPlan";
import { decisionLabels, phaseLabels, responseLabels } from "../lib/labels";
import { listPlanAdaptations, recalculateWeekReview, type AdaptationEvent } from "../api/seasonPlans";
import "../styles/ProgressPage.css";

export function ProgressPage() {
  const { plan, status, error, refresh } = useSeasonPlan();
  const [recalculatingWeek, setRecalculatingWeek] = useState<string | null>(null);
  const [recalculationMessage, setRecalculationMessage] = useState<string | null>(null);
  const [adaptations, setAdaptations] = useState<AdaptationEvent[]>([]);
  const evaluatedWeeks = plan?.weeks.filter((week) => week.review !== null) ?? [];

  useEffect(() => {
    if (plan === null) return;
    void listPlanAdaptations(plan.id).then(setAdaptations).catch(() => setAdaptations([]));
  }, [plan]);

  const plannedTss = evaluatedWeeks.reduce(
    (total, week) =>
      total + (week.review?.planned_tss ?? 0),
    0,
  );

  const completedTss = evaluatedWeeks.reduce(
    (total, week) =>
      total + (week.review?.registered_tss ?? 0),
    0,
  );

  const plannedWorkouts = evaluatedWeeks.reduce(
    (total, week) => total + (week.review?.planned_workout_count ?? 0),
    0,
  );
  const completedWorkouts = evaluatedWeeks.reduce(
    (total, week) => total + (week.review?.completed_workout_count ?? 0),
    0,
  );
  const adherence = plannedWorkouts > 0 ? (completedWorkouts / plannedWorkouts) * 100 : 0;

  const aerobicResponses = evaluatedWeeks
    .map((week) => week.review?.response_median ?? null)
    .filter(
      (value): value is number =>
        value !== null,
    );

  const meanAerobicResponse =
    aerobicResponses.length > 0
      ? aerobicResponses.reduce(
          (total, value) => total + value,
          0,
        ) / aerobicResponses.length
      : null;

  const maximumTss = Math.max(1, ...evaluatedWeeks.flatMap((week) => [
    week.review?.planned_tss ?? 0,
    week.review?.registered_tss ?? 0,
  ]));
  const registeredActivities = evaluatedWeeks.reduce(
    (total, week) => total + (week.review?.activity_count ?? 0),
    0,
  );
  const activitiesWithoutTss = evaluatedWeeks.reduce(
    (total, week) => total + (week.review?.activities_without_tss ?? 0),
    0,
  );
  const estimatedRpeLoad = evaluatedWeeks.reduce(
    (total, week) => total + (week.review?.registered_rpe_load ?? 0),
    0,
  );
  const activitiesWithoutLoad = evaluatedWeeks.reduce(
    (total, week) => total + (week.review?.activities_without_load ?? 0),
    0,
  );
  const activitiesWithoutResponse = evaluatedWeeks.reduce(
    (total, week) => total + Math.max(
      0,
      (week.review?.activity_count ?? 0) - (week.review?.response_count ?? 0),
    ),
    0,
  );

  async function recalculate(weekId: string) {
    setRecalculatingWeek(weekId);
    setRecalculationMessage(null);
    try {
      await recalculateWeekReview(weekId);
      await refresh();
      setRecalculationMessage("La revisión se ha actualizado con los datos actuales.");
    } catch (cause) {
      setRecalculationMessage(cause instanceof Error ? cause.message : "No se pudo actualizar la revisión.");
    } finally {
      setRecalculatingWeek(null);
    }
  }

  if (status === "loading") return <main className="progress-page"><p>Cargando evolución…</p></main>;
  if (status === "error") return <main className="progress-page"><p>{error ?? "No se pudo cargar la evolución."}</p><button type="button" onClick={() => void refresh()}>Reintentar</button></main>;

  return (
    <main className="progress-page">
      <header className="progress-page__header">
        <p className="progress-page__eyebrow">
          Seguimiento
        </p>

        <h1>Evolución</h1>

        <p>
          Compara la planificación con el entrenamiento
          realizado y revisa tu respuesta aeróbica.
        </p>
      </header>

      {evaluatedWeeks.length === 0 && (
        <p className="progress-page__demo-notice">
          La evolución aparecerá cuando finalices y revises tu primera semana de entrenamiento.
        </p>
      )}

      {evaluatedWeeks.length > 0 && (
        <section className="progress-page__data-quality">
          <div>
            <strong>{registeredActivities} actividades registradas en semanas revisadas</strong>
            <p>
              {activitiesWithoutTss === 0
                ? "Todas tienen TSS."
                : `${activitiesWithoutTss} sin TSS; ${estimatedRpeLoad.toFixed(0)} RPE·min se mantienen como carga estimada separada.`}{" "}
              {activitiesWithoutResponse === 0
                ? "Todas tienen desacoplamiento aeróbico."
                : `${activitiesWithoutResponse} sin desacoplamiento aeróbico.`}
            </p>
            <small>
              Si corriges una actividad después del cierre, actualiza la revisión de su semana.
            </small>
            {recalculationMessage !== null && <span role="status">{recalculationMessage}</span>}
          </div>
        </section>
      )}

      <section className="progress-page__metrics">
        <article>
          <span>Cumplimiento</span>
          <strong>
            {adherence.toFixed(0)} %
          </strong>
          <small>
            Sobre semanas evaluadas
          </small>
        </article>

        <article>
          <span>TSS planificado</span>
          <strong>
            {plannedTss.toFixed(0)}
          </strong>
          <small>
            Carga acumulada evaluada
          </small>
        </article>

        <article>
          <span>{completedTss > 0 ? "TSS realizado" : "Carga estimada"}</span>
          <strong>
            {completedTss > 0 ? completedTss.toFixed(0) : `${estimatedRpeLoad.toFixed(0)} RPE·min`}
          </strong>
          <small>
            {activitiesWithoutLoad > 0 ? `${activitiesWithoutLoad} actividades sin datos de carga` : "Carga completada"}
          </small>
        </article>

        <article>
          <span>Respuesta aeróbica media</span>
          <strong>
            {meanAerobicResponse === null
              ? "Sin datos"
              : `${meanAerobicResponse.toFixed(1)} %`}
          </strong>
          <small>
            Actividades registradas
          </small>
        </article>
      </section>

      <section className="progress-chart">
        <header>
          <div>
            <h2>Carga por semana</h2>
            <p>
              TSS planificado frente al realizado. La carga RPE se informa aparte porque utiliza otra escala.
            </p>
          </div>

          <div className="progress-chart__legend">
            <span>
              <i className="progress-chart__planned" />
              Planificado
            </span>

            <span>
              <i className="progress-chart__completed" />
              Realizado
            </span>
          </div>
        </header>

        <div className="progress-chart__weeks">
          {evaluatedWeeks.map((week) => {
            const plannedHeight =
              (
                (week.review?.planned_tss ?? 0) /
                maximumTss
              ) * 100;

            const completedHeight =
              (
                (week.review?.registered_tss ?? 0) /
                maximumTss
              ) * 100;

            return (
              <article
                key={week.week_start}
                className="progress-chart__week"
              >
                <div className="progress-chart__bars">
                  <div
                    className="progress-chart__planned"
                    style={{
                      height: `${plannedHeight}%`,
                    }}
                    title={`${week.review?.planned_tss ?? 0} TSS planificados`}
                  />

                  <div
                    className="progress-chart__completed"
                    style={{
                      height: `${completedHeight}%`,
                    }}
                    title={`${week.review?.registered_tss ?? 0} TSS realizados`}
                  />
                </div>

                <strong>
                  {format(
                    parseISO(week.week_start),
                    "d MMM",
                    {
                      locale: es,
                    },
                  )}
                </strong>

                <small>{phaseLabels[week.phase as keyof typeof phaseLabels]}</small>
                <button
                  type="button"
                  disabled={recalculatingWeek === week.id}
                  onClick={() => void recalculate(week.id)}
                >
                  {recalculatingWeek === week.id ? "Actualizando…" : "Actualizar revisión"}
                </button>
                <Link to={`/plans/${plan?.id}/weeks/${week.id}`}>Ver detalle</Link>
              </article>
            );
          })}
        </div>
      </section>

      {adaptations.length > 0 && (
        <section className="progress-adaptations">
          <header>
            <h2>Historial de adaptaciones</h2>
            <p>Qué cambió en cada cierre semanal y por qué.</p>
          </header>
          <div className="progress-adaptations__list">
            {adaptations.map((adaptation) => {
              const sourceWeek = plan?.weeks.find((week) => week.id === adaptation.source_week_id);
              const targetWeek = plan?.weeks.find((week) => week.id === adaptation.target_week_id);
              const provisional = adaptation.provisional_target_tss;
              const requested = targetWeek?.requested_target_tss ?? null;
              const adapted = adaptation.adapted_target_tss;
              const difference = provisional !== null && adapted !== null ? adapted - provisional : null;
              const percentage = difference !== null && provisional !== null && provisional !== 0
                ? (difference / provisional) * 100
                : null;
              return (
                <article key={adaptation.id}>
                  <div>
                    <span>{sourceWeek === undefined ? "Semana revisada" : `Semana del ${format(parseISO(sourceWeek.week_start), "d MMM", { locale: es })}`}</span>
                    <strong>
                      {responseLabels[adaptation.response_classification as keyof typeof responseLabels]}
                      {adaptation.load_decision !== null && ` · ${decisionLabels[adaptation.load_decision as keyof typeof decisionLabels]}`}
                    </strong>
                    {sourceWeek?.review !== null && sourceWeek?.review !== undefined && (
                      <p>
                        Se registraron {sourceWeek.review.registered_tss.toFixed(0)} de {sourceWeek.review.planned_tss.toFixed(0)} TSS planificados.
                      </p>
                    )}
                    <small>
                      {adaptation.observed_aerobic_decoupling === null ? "Sin desacoplamiento disponible" : `Desacoplamiento registrado: ${adaptation.observed_aerobic_decoupling.toFixed(1)} %`}
                    </small>
                  </div>
                  <div className="progress-adaptations__change">
                    <span>Semana siguiente</span>
                    {difference === null ? <strong>Fin del plan</strong> : (
                      <dl>
                        <div><dt>Previsión de temporada</dt><dd>{provisional?.toFixed(0) ?? "—"} TSS</dd></div>
                        <div><dt>Objetivo tras la revisión</dt><dd>{requested?.toFixed(0) ?? "—"} TSS</dd></div>
                        <div><dt>Plan factible generado</dt><dd>{adapted?.toFixed(0) ?? "—"} TSS</dd></div>
                      </dl>
                    )}
                    {difference !== null && (
                      <small>
                        La previsión cambia {difference >= 0 ? "+" : ""}{difference.toFixed(0)} TSS
                        {percentage !== null && ` (${percentage >= 0 ? "+" : ""}${percentage.toFixed(1)} %)`}.
                        {requested !== null && adapted !== null && Math.abs(requested - adapted) > 0.01
                          ? ` La disponibilidad ajusta el objetivo solicitado en ${(adapted - requested).toFixed(0)} TSS.`
                          : " El objetivo solicitado cabe en la disponibilidad del ciclista."}
                      </small>
                    )}
                    {targetWeek !== undefined && <Link to={`/plans/${plan?.id}/weeks/${targetWeek.id}`}>Ver semana adaptada</Link>}
                  </div>
                </article>
              );
            })}
          </div>
        </section>
      )}

      <section className="progress-responses">
        <header>
          <h2>Respuesta aeróbica registrada</h2>
          <p>
            Desacoplamiento introducido en las
            actividades realizadas.
          </p>
        </header>

        {aerobicResponses.length === 0 ? (
          <div className="progress-responses__empty">
            Añade actividades con desacoplamiento
            aeróbico para visualizar su evolución.
          </div>
        ) : (
          <div className="progress-responses__values">
            {evaluatedWeeks
              .filter((week) => week.review?.response_median !== null)
              .map((week) => (
                <article key={week.id}>
                  <span>Semana del {format(parseISO(week.week_start), "d MMM", { locale: es })}</span>
                  <strong>
                    {week.review?.response_median?.toFixed(1)}
                    %
                  </strong>
                </article>
              ))}
          </div>
        )}
      </section>
    </main>
  );
}
