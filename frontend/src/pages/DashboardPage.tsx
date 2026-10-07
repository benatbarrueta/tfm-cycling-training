import { addDays, format, parseISO } from "date-fns";
import { es } from "date-fns/locale";
import { Link } from "react-router-dom";
import { useActivities } from "../hooks/useActivities";
import { dayLabels, decisionLabels, responseLabels, workoutLabels } from "../lib/labels";
import { trainingPlanMock } from "../mocks/trainingPlan";
import "../styles/DashboardPage.css";

export function DashboardPage() {
  const { activities } = useActivities();
  const { plan, reference_date } =
    trainingPlanMock;

  const weekStart = parseISO(reference_date);
  const weekEnd = addDays(weekStart, 6);

  const weekStartText = format(
    weekStart,
    "yyyy-MM-dd",
  );

  const weekEndText = format(
    weekEnd,
    "yyyy-MM-dd",
  );

  const weeklyActivities = activities.filter(
    (activity) =>
      activity.started_at.slice(0, 10) >= weekStartText &&
      activity.started_at.slice(0, 10) <= weekEndText,
  );

  const completedTss = weeklyActivities.reduce(
    (total, activity) =>
      total + (activity.tss ?? 0),
    0,
  );

  const progress =
    plan.estimated_total_tss > 0
      ? Math.min(
          100,
          (
            completedTss /
            plan.estimated_total_tss
          ) * 100,
        )
      : 0;

  const nextWorkout = plan.workouts[0];

  const nextPrediction =
    plan.workout_response_predictions.find(
      (prediction) =>
        prediction.day === nextWorkout?.day,
    );

  return (
    <main className="dashboard">
      <header className="dashboard__welcome">
        <div>
          <p className="dashboard__eyebrow">
            Resumen semanal
          </p>

          <h1>Tu entrenamiento</h1>

          <p>
            Semana del{" "}
            {format(
              weekStart,
              "d 'de' MMMM",
              { locale: es },
            )}{" "}
            al{" "}
            {format(
              weekEnd,
              "d 'de' MMMM",
              { locale: es },
            )}
          </p>
        </div>

        <Link
          className="dashboard__primary-link"
          to="/calendar"
        >
          Abrir calendario
        </Link>
      </header>

      <section className="dashboard__metrics">
        <article>
          <span>Carga semanal</span>
          <strong>
            {completedTss.toFixed(0)} /{" "}
            {plan.estimated_total_tss.toFixed(0)}
          </strong>
          <small>TSS completado</small>
        </article>

        <article>
          <span>Tiempo planificado</span>
          <strong>
            {(
              plan.total_duration_minutes / 60
            ).toFixed(1)}{" "}
            h
          </strong>
          <small>
            {plan.workouts.length} sesiones
          </small>
        </article>

        <article>
          <span>Respuesta aeróbica</span>
          <strong>
            {responseLabels[
              plan.aerobic_response
            ]}
          </strong>
          <small>
            {plan.expected_aerobic_decoupling
              ?.toFixed(1) ?? "—"}{" "}
            % previsto
          </small>
        </article>

        <article>
          <span>Decisión de carga</span>
          <strong>
            {plan.load_decision !== null
              ? decisionLabels[
                  plan.load_decision
                ]
              : "Sin determinar"}
          </strong>
          <small>
            Objetivo:{" "}
            {plan.target_tss.toFixed(0)} TSS
          </small>
        </article>
      </section>

      <section className="dashboard__content">
        <article className="dashboard__progress">
          <header>
            <div>
              <span>Progreso semanal</span>
              <strong>
                {progress.toFixed(0)} %
              </strong>
            </div>

            <Link to="/calendar">
              Ver semana
            </Link>
          </header>

          <div
            className="dashboard__progress-track"
            role="progressbar"
            aria-valuenow={progress}
            aria-valuemin={0}
            aria-valuemax={100}
          >
            <span
              style={{
                width: `${progress}%`,
              }}
            />
          </div>

          <p>
            Has registrado{" "}
            {weeklyActivities.length} actividades
            durante esta semana.
          </p>
        </article>

        <article className="dashboard__next">
          <header>
            <span>Próxima sesión</span>

            <Link to="/plan">
              Ver plan
            </Link>
          </header>

          {nextWorkout === undefined ? (
            <p>No hay sesiones planificadas.</p>
          ) : (
            <>
              <h2>
                {workoutLabels[nextWorkout.workout_type]}
              </h2>

              <dl>
                <div>
                  <dt>Día</dt>
                  <dd>{dayLabels[nextWorkout.day]}</dd>
                </div>

                <div>
                  <dt>Duración</dt>
                  <dd>
                    {nextWorkout.duration_minutes ??
                      "—"}{" "}
                    min
                  </dd>
                </div>

                <div>
                  <dt>TSS</dt>
                  <dd>
                    {nextWorkout.estimated_tss
                      ?.toFixed(0) ?? "—"}
                  </dd>
                </div>
              </dl>

              {nextPrediction !== undefined && (
                <p>
                  Respuesta aeróbica prevista:{" "}
                  <strong>
                    {nextPrediction
                      .predicted_aerobic_decoupling
                      .toFixed(1)}
                    %
                  </strong>
                </p>
              )}
            </>
          )}
        </article>
      </section>
    </main>
  );
}