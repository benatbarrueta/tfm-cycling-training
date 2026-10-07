import { format, parseISO } from "date-fns";
import { es } from "date-fns/locale";
import { useActivities } from "../hooks/useActivities";
import { seasonPlanMock } from "../mocks/seasonPlan";
import "../styles/ProgressPage.css";

export function ProgressPage() {
  const { activities } = useActivities();
  const weeks = seasonPlanMock.weeks;

  const evaluatedWeeks = weeks.filter(
    (week) =>
      week.status === "COMPLETED" ||
      week.status === "ADAPTED",
  );

  const plannedTss = evaluatedWeeks.reduce(
    (total, week) =>
      total + week.planned_tss,
    0,
  );

  const completedTss = evaluatedWeeks.reduce(
    (total, week) =>
      total + week.completed_tss,
    0,
  );

  const adherence =
    plannedTss > 0
      ? (completedTss / plannedTss) * 100
      : 0;

  const aerobicResponses = activities
    .map(
      (activity) =>
        activity.aerobic_decoupling,
    )
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

  const maximumTss = Math.max(
    ...weeks.flatMap((week) => [
      week.planned_tss,
      week.completed_tss,
    ]),
  );

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

      <p className="progress-page__demo-notice">
        Vista de demostración: las gráficas históricas todavía utilizan datos
        de ejemplo. Las actividades recientes se muestran por separado.
      </p>

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
          {weeks.map((week) => {
            const plannedHeight =
              (
                week.planned_tss /
                maximumTss
              ) * 100;

            const completedHeight =
              (
                week.completed_tss /
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
                    title={`${week.planned_tss} TSS planificados`}
                  />

                  <div
                    className="progress-chart__completed"
                    style={{
                      height: `${completedHeight}%`,
                    }}
                    title={`${week.completed_tss} TSS realizados`}
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

                <small>{week.phase}</small>
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
            {activities
              .filter(
                (activity) =>
                  activity.aerobic_decoupling !==
                  null,
              )
              .map((activity) => (
                <article key={activity.id}>
                  <span>{new Date(activity.started_at).toLocaleDateString("es-ES")}</span>
                  <strong>
                    {activity.aerobic_decoupling
                      ?.toFixed(1)}
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