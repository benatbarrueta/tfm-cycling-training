import {
  differenceInCalendarWeeks,
  format,
  parseISO,
} from "date-fns";
import { es } from "date-fns/locale";
import { WeeklyPlan } from "../components/WeeklyPlan";
import { useSeasonPlan } from "../hooks/useSeasonPlan";
import type { AerobicResponse, TrainingPlan, WeekDay } from "../types/training";
import { getCurrentDate, getTodayInTimeZone, getWeekLabel, getWeekTemporalState } from "../lib/temporal";
import "../styles/SeasonPlanPage.css";

const phaseLabels = {
  BASE: "Base",
  BUILD: "Construcción",
  PEAK: "Pico",
  TAPER: "Descarga",
} as const;

export function SeasonPlanPage() {
  const { plan: seasonPlan, status, error, create, refresh } = useSeasonPlan();
  if (status === "loading") return <main className="season-plan"><p>Cargando planificación...</p></main>;
  if (status === "error") {
    return (
      <main className="season-plan">
        <p>{error ?? "No se ha podido cargar la planificación."}</p>
        <button type="button" onClick={() => void refresh()}>Reintentar</button>
      </main>
    );
  }
  if (seasonPlan === null) {
    return (
      <main className="season-plan">
        <p>Aún no tienes un plan de temporada.</p>
        <button type="button" onClick={() => void create("Plan de temporada")}>
          Crear mi planificación
        </button>
      </main>
    );
  }

  const objectiveDate = parseISO(
    seasonPlan.target_date,
  );
  const today = getTodayInTimeZone(getCurrentDate(), "Europe/Madrid");

  const activeWeek = seasonPlan.weeks.find(
    (week) => week.status === "ACTIVE",
  );

  const activeTrainingPlan: TrainingPlan | null = activeWeek === undefined || activeWeek.workouts.length === 0
    ? null
    : {
        requested_target_tss: activeWeek.requested_target_tss,
        target_tss: activeWeek.adapted_target_tss ?? activeWeek.provisional_target_tss,
        feasibility_adjusted: activeWeek.requested_target_tss !== activeWeek.adapted_target_tss,
        estimated_total_tss: activeWeek.estimated_total_tss ?? 0,
        estimated_tss_difference: 0,
        total_duration_minutes: activeWeek.workouts.reduce((total, workout) => total + (workout.duration_minutes ?? 0), 0),
        expected_aerobic_decoupling: activeWeek.expected_aerobic_decoupling,
        response_prediction_method: activeWeek.response_prediction_method ?? "unavailable",
        response_evaluated_target_tss: null,
        aerobic_response: (activeWeek.workouts[0].aerobic_response ?? "UNKNOWN") as AerobicResponse,
        load_decision: activeWeek.load_decision as TrainingPlan["load_decision"],
        workout_response_predictions: activeWeek.workouts
          .filter((workout) => workout.predicted_aerobic_decoupling !== null)
          .map((workout) => ({
            day: workout.day as WeekDay,
            session_date: workout.scheduled_date,
            predicted_aerobic_decoupling: workout.predicted_aerobic_decoupling ?? 0,
            aerobic_response: (workout.aerobic_response ?? "UNKNOWN") as AerobicResponse,
            outside_training_range_features: workout.outside_training_range_features ?? [],
          })),
        workouts: activeWeek.workouts.map((workout) => ({
          day: workout.day as WeekDay,
          workout_type: workout.workout_type as TrainingPlan["workouts"][number]["workout_type"],
          target_tss: workout.target_tss,
          estimated_tss: workout.estimated_tss,
          duration_minutes: workout.duration_minutes,
          target_power_min: workout.target_power_min,
          target_power_max: workout.target_power_max,
          warmup: workout.warmup,
          intervals: workout.intervals,
          cooldown: workout.cooldown,
        })),
      };

  const maximumTss = Math.max(
    ...seasonPlan.weeks.map(
      (week) => week.provisional_target_tss,
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

            <h1>{seasonPlan.name}</h1>

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
                  week.provisional_target_tss /
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
                    {getWeekLabel(
                      week.status,
                      getWeekTemporalState(today, week.week_start, week.week_end),
                    )}
                  </span>

                  <div className="season-week__chart">
                    <div
                      style={{
                        height: `${height}%`,
                      }}
                    />
                  </div>

                  <strong>
                    {week.provisional_target_tss.toFixed(0)} TSS
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
                    {phaseLabels[week.phase as keyof typeof phaseLabels]}
                  </small>

                </article>
              );
            })}
          </div>
        </section>

      </main>

      {activeTrainingPlan && <WeeklyPlan plan={activeTrainingPlan} />}
    </>
  );
}