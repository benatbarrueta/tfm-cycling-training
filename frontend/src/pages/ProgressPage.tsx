import { useState } from "react";
import { format, parseISO } from "date-fns";
import { es } from "date-fns/locale";
import { useSeasonPlan } from "../hooks/useSeasonPlan";
import { phaseLabels } from "../lib/labels";
import { recalculateWeekReview } from "../api/seasonPlans";
import "../styles/ProgressPage.css";

export function ProgressPage() {
  const { plan, status, error, refresh } = useSeasonPlan();
  const [recalculatingWeek, setRecalculatingWeek] = useState<string | null>(null);
  const [recalculationMessage, setRecalculationMessage] = useState<string | null>(null);
  const evaluatedWeeks = plan?.weeks.filter((week) => week.review !== null) ?? [];

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

  const adherence =
    plannedTss > 0
      ? (completedTss / plannedTss) * 100
      : 0;

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
                : `${activitiesWithoutTss} sin TSS.`}{" "}
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
          <span>TSS realizado</span>
          <strong>
            {completedTss.toFixed(0)}
          </strong>
          <small>
            Carga completada
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
              TSS planificado frente al realizado.
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
              </article>
            );
          })}
        </div>
      </section>

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
