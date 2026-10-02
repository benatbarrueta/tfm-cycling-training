import {
  differenceInCalendarWeeks,
  format,
  parseISO,
} from "date-fns";
import { es } from "date-fns/locale";
import { WeeklyPlan } from "../components/WeeklyPlan";
import { seasonPlanMock } from "../mocks/seasonPlan";
import "../styles/SeasonPlanPage.css";

const phaseLabels = {
  BASE: "Base",
  BUILD: "Construcción",
  PEAK: "Pico",
  TAPER: "Descarga",
} as const;

const statusLabels = {
  PROVISIONAL: "Provisional",
  ACTIVE: "Semana activa",
  COMPLETED: "Completada",
  ADAPTED: "Adaptada",
} as const;

export function SeasonPlanPage() {
  const seasonPlan = seasonPlanMock;

  const objectiveDate = parseISO(
    seasonPlan.objective_date,
  );

  const activeWeek = seasonPlan.weeks.find(
    (week) => week.status === "ACTIVE",
  );

  const maximumTss = Math.max(
    ...seasonPlan.weeks.map(
      (week) => week.planned_tss,
    ),
  );

  const remainingWeeks =
    activeWeek === undefined
      ? 0
      : differenceInCalendarWeeks(
          objectiveDate,
          parseISO(activeWeek.week_start),
          {
            weekStartsOn: 1,
          },
        );

  return (
    <>
      <main className="season-plan">
        <header className="season-plan__header">
          <div>
            <p className="season-plan__eyebrow">
              Planificación
            </p>

            <h1>{seasonPlan.objective_name}</h1>

            <p>
              Objetivo el{" "}
              {format(
                objectiveDate,
                "d 'de' MMMM 'de' yyyy",
                {
                  locale: es,
                },
              )}
            </p>
          </div>

          <div className="season-plan__remaining">
            <strong>{remainingWeeks}</strong>
            <span>semanas restantes</span>
          </div>
        </header>

        <section className="season-plan__phases">
          {Object.entries(phaseLabels).map(
            ([phase, label]) => (
              <div key={phase}>
                <span
                  className={`season-plan__phase-dot season-plan__phase-dot--${phase.toLowerCase()}`}
                />
                {label}
              </div>
            ),
          )}
        </section>

        <section className="season-plan__timeline">
          <header>
            <div>
              <h2>Progresión de carga</h2>
              <p>
                Las semanas futuras son provisionales y
                se revisarán según tu respuesta.
              </p>
            </div>
          </header>

          <div className="season-plan__weeks">
            {seasonPlan.weeks.map((week) => {
              const height =
                (
                  week.planned_tss /
                  maximumTss
                ) * 100;

              return (
                <article
                  key={week.week_start}
                  className={[
                    "season-week",
                    `season-week--${week.phase.toLowerCase()}`,
                    `season-week--${week.status.toLowerCase()}`,
                  ].join(" ")}
                >
                  <span className="season-week__status">
                    {statusLabels[week.status]}
                  </span>

                  <div className="season-week__chart">
                    <div
                      style={{
                        height: `${height}%`,
                      }}
                    />
                  </div>

                  <strong>
                    {week.planned_tss.toFixed(0)} TSS
                  </strong>

                  <span>
                    {format(
                      parseISO(week.week_start),
                      "d MMM",
                      {
                        locale: es,
                      },
                    )}
                  </span>

                  <small>
                    {phaseLabels[week.phase]}
                  </small>

                  {week.completed_tss > 0 && (
                    <p>
                      Realizado:{" "}
                      {week.completed_tss.toFixed(0)} TSS
                    </p>
                  )}
                </article>
              );
            })}
          </div>
        </section>

        {activeWeek?.adaptation_reason && (
          <aside className="season-plan__adaptation">
            <strong>
              Adaptación de la semana activa
            </strong>

            <p>
              {activeWeek.adaptation_reason}
            </p>
          </aside>
        )}
      </main>

      {activeWeek?.training_plan && (
        <WeeklyPlan
          plan={activeWeek.training_plan}
        />
      )}
    </>
  );
}