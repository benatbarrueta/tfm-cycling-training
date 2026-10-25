import { useMemo, useState } from "react";
import { useSearchParams } from "react-router-dom";
import {
  addDays,
  addMonths,
  addWeeks,
  eachDayOfInterval,
  endOfMonth,
  endOfWeek,
  format,
  isSameMonth,
  parseISO,
  startOfMonth,
  startOfWeek,
} from "date-fns";
import { es } from "date-fns/locale";
import { ActivityForm } from "../components/ActivityForm";
import { CalendarToolbar } from "../components/CalendarToolbar";
import {
  CompletedActivityCard,
} from "../components/CompletedActivityCard";
import { useActivities } from "../hooks/useActivities";
import { useSeasonPlan } from "../hooks/useSeasonPlan";
import { phaseLabels, workoutLabels } from "../lib/labels";
import { getCurrentDate, getTodayInTimeZone, getWeekLabel, getWeekTemporalState } from "../lib/temporal";
import { summarizeWeeklyActivities } from "../lib/weeklyActivitySummary";
import { localDateToUtcIso } from "../lib/timezone";
import type {
  CalendarDay,
  CalendarView,
} from "../types/calendar";
import type { ActivityInput } from "../api/activities";
import type { PlannedWeek } from "../api/seasonPlans";
import "../styles/CalendarPage.css";

const statusLabels = {
  rest: "Descanso",
  planned: "Planificado",
  provisional: "Por definir",
  completed: "Completado",
  partial: "Parcial",
  missed: "No realizado",
} as const;

const weekStatusLabels = {
  PROVISIONAL: "Provisional",
  ACTIVE: "Activa",
  COMPLETED: "Completada",
  ADAPTED: "Adaptada",
} as const;

function capitalize(value: string): string {
  return value.charAt(0).toUpperCase() + value.slice(1);
}

function getVisibleDates(
  selectedDate: Date,
  view: CalendarView,
): Date[] {
  if (view === "day") {
    return [selectedDate];
  }

  if (view === "week") {
    const weekStart = startOfWeek(selectedDate, {
      weekStartsOn: 1,
    });

    return eachDayOfInterval({
      start: weekStart,
      end: endOfWeek(selectedDate, {
        weekStartsOn: 1,
      }),
    });
  }

  const monthStart = startOfMonth(selectedDate);
  const monthEnd = endOfMonth(selectedDate);

  return eachDayOfInterval({
    start: startOfWeek(monthStart, {
      weekStartsOn: 1,
    }),
    end: endOfWeek(monthEnd, {
      weekStartsOn: 1,
    }),
  });
}

function getActivityRange(dates: Date[]) {
  const first = dates[0];
  const last = dates[dates.length - 1];
  const startDate = format(first, "yyyy-MM-dd");
  const endDate = format(addDays(last, 1), "yyyy-MM-dd");

  return {
    start: localDateToUtcIso(startDate, "Europe/Madrid"),
    end: localDateToUtcIso(endDate, "Europe/Madrid"),
    limit: 100,
  };
}

function getCalendarTitle(
  selectedDate: Date,
  view: CalendarView,
): string {
  if (view === "day") {
    return capitalize(
      format(
        selectedDate,
        "EEEE d 'de' MMMM",
        {
          locale: es,
        },
      ),
    );
  }

  if (view === "week") {
    const start = startOfWeek(selectedDate, {
      weekStartsOn: 1,
    });

    const end = endOfWeek(selectedDate, {
      weekStartsOn: 1,
    });

    return `${format(start, "d MMM", {
      locale: es,
    })} – ${format(end, "d MMM yyyy", {
      locale: es,
    })}`;
  }

  return capitalize(
    format(
      selectedDate,
      "MMMM 'de' yyyy",
      {
        locale: es,
      },
    ),
  );
}

export function CalendarPage() {
  const { plan: seasonPlan, status, error, refresh } = useSeasonPlan();
  const today = getTodayInTimeZone(getCurrentDate(), "Europe/Madrid");
  const [searchParams] = useSearchParams();

  const [view, setView] =
    useState<CalendarView>(() =>
      searchParams.get("view") === "week" ? "week" : "month",
    );

  const [selectedDate, setSelectedDate] =
    useState(() =>
      searchParams.get("date")
        ? parseISO(searchParams.get("date") ?? today)
        : getCurrentDate(),
    );

  const activityFilters = useMemo(() => {
    return getActivityRange(getVisibleDates(selectedDate, view));
  }, [selectedDate, view]);

  const [
    showActivityForm,
    setShowActivityForm,
  ] = useState(false);

  const { activities, addActivity, removeActivity, linkActivity } = useActivities(activityFilters);

  const visibleDates = useMemo(
    () => getVisibleDates(selectedDate, view),
    [selectedDate, view],
  );

  const selectedDateText = format(
    selectedDate,
    "yyyy-MM-dd",
  );

  const selectedWeek: PlannedWeek | null =
    seasonPlan?.weeks.find(
      (week) =>
        selectedDateText >= week.week_start &&
        selectedDateText <= week.week_end,
    ) ?? null;
  const calendarWeekStart = format(startOfWeek(selectedDate, { weekStartsOn: 1 }), "yyyy-MM-dd");
  const calendarWeekEnd = format(endOfWeek(selectedDate, { weekStartsOn: 1 }), "yyyy-MM-dd");
  const calendarWeekActivities = summarizeWeeklyActivities(
    activities,
    calendarWeekStart,
    calendarWeekEnd,
    "Europe/Madrid",
  );

  const calendarDays = useMemo<CalendarDay[]>(
    () =>
      visibleDates.map((date) => {
        const isoDate = format(
          date,
          "yyyy-MM-dd",
        );

        const plannedWeek =
          seasonPlan?.weeks.find(
            (week) =>
              isoDate >= week.week_start &&
              isoDate <= week.week_end,
          ) ?? null;

        const plannedWorkout =
          plannedWeek?.workouts.find((workout) => workout.scheduled_date === isoDate) ?? null;
        const prediction = plannedWorkout;

        const dayActivities =
          activities.filter((activity) =>
            getTodayInTimeZone(activity.started_at, "Europe/Madrid") === isoDate,
          );

        let status: CalendarDay["status"];

        const linkedActivities = plannedWorkout === null
          ? []
          : dayActivities.filter((activity) => activity.planned_workout_id === plannedWorkout.id);
        const completedTss = linkedActivities.reduce(
          (total, activity) => total + (activity.tss ?? 0),
          0,
        );
        const plannedTss = plannedWorkout?.estimated_tss ?? plannedWorkout?.target_tss ?? 0;

        if (linkedActivities.length > 0 && plannedTss > 0 && completedTss < plannedTss * 0.8) {
          status = "partial";
        } else if (linkedActivities.length > 0) {
          status = "completed";
        } else if (plannedWorkout !== null) {
          status = isoDate < today ? "missed" : "planned";
        } else if (
          plannedWeek?.status === "PROVISIONAL"
        ) {
          status = "provisional";
        } else {
          status = "rest";
        }

        return {
          date: isoDate,
          planned_week: plannedWeek,
          planned_workout: plannedWorkout,
          activities: dayActivities,
          response_prediction: prediction,
          status,
        };
      }),
    [
      activities,
      seasonPlan,
      today,
      visibleDates,
    ],
  );

  if (status === "loading") return <main className="calendar-page"><p>Cargando planificación...</p></main>;
  if (status === "error") return <main className="calendar-page"><p>{error ?? "No se ha podido cargar la planificación."}</p><button type="button" onClick={() => void refresh()}>Reintentar</button></main>;

  function movePeriod(direction: -1 | 1) {
    setSelectedDate((currentDate) => {
      if (view === "month") {
        return addMonths(
          currentDate,
          direction,
        );
      }

      if (view === "week") {
        return addWeeks(
          currentDate,
          direction,
        );
      }

      return addDays(
        currentDate,
        direction,
      );
    });

    setShowActivityForm(false);
  }

  function openDay(date: string) {
    setSelectedDate(parseISO(date));
    setView("day");
    setShowActivityForm(false);
  }

  function goToToday() {
    setSelectedDate(parseISO(today));
    setShowActivityForm(false);
  }

  function changeView(
    nextView: CalendarView,
  ) {
    setView(nextView);
    setShowActivityForm(false);
  }

  async function submitActivity(activity: ActivityInput) {
    const created = await addActivity(activity);
    const workout = calendarDays[0]?.planned_workout;
    if (workout !== null && workout !== undefined) {
      await linkActivity(created.id, workout.id);
    }
    setView("day");
    setShowActivityForm(false);
  }

  return (
    <main className="calendar-page">
      <CalendarToolbar
        title={getCalendarTitle(
          selectedDate,
          view,
        )}
        view={view}
        onViewChange={changeView}
        onPrevious={() => movePeriod(-1)}
        onToday={goToToday}
        onNext={() => movePeriod(1)}
      />

      {seasonPlan === null ? (
        <section className="calendar-page__week-summary">
          <p>Aún no tienes un plan de temporada. Las actividades registradas siguen disponibles.</p>
          <strong>TSS registrado: {calendarWeekActivities.knownTss.toFixed(0)}</strong>
        </section>
      ) : selectedWeek !== null ? (
        <section
          className={[
            "calendar-page__week-summary",
            `calendar-page__week-summary--${selectedWeek.status.toLowerCase()}`,
          ].join(" ")}
        >
          <div>
            <span>
              {phaseLabels[selectedWeek.phase as keyof typeof phaseLabels]}
            </span>

            <strong>
              {getWeekLabel(selectedWeek.status, getWeekTemporalState(today, selectedWeek.week_start, selectedWeek.week_end))}
            </strong>
          </div>

          <dl>
            <div>
              <dt>TSS previsto</dt>
              <dd>
                {(selectedWeek.adapted_target_tss ?? selectedWeek.estimated_total_tss ?? selectedWeek.provisional_target_tss).toFixed(0)}
              </dd>
            </div>

            <div>
              <dt>TSS registrado</dt>
              <dd>
                {summarizeWeeklyActivities(activities, selectedWeek.week_start, selectedWeek.week_end, "Europe/Madrid").knownTss.toFixed(0)}
              </dd>
            </div>
          </dl>

          {selectedWeek.status ===
            "PROVISIONAL" && (
            <p>
              Las sesiones concretas se generarán
              cuando esta semana pase a estar activa.
            </p>
          )}
        </section>
      ) : (
        <section className="calendar-page__week-summary">
          <p>Este intervalo no pertenece a una semana planificada.</p>
          <strong>TSS registrado: {calendarWeekActivities.knownTss.toFixed(0)}</strong>
        </section>
      )}

      {view !== "day" && (
        <div className="calendar-page__weekdays">
          {[
            "Lun",
            "Mar",
            "Mié",
            "Jue",
            "Vie",
            "Sáb",
            "Dom",
          ].map((day) => (
            <span key={day}>{day}</span>
          ))}
        </div>
      )}

      <section
        className={[
          "calendar-page__grid",
          `calendar-page__grid--${view}`,
        ].join(" ")}
      >
        {calendarDays.map((day) => {
          const date = parseISO(day.date);
          const workout = day.planned_workout;
          const prediction =
            day.response_prediction;
          const plannedWeek =
            day.planned_week;

          const isWeekStart =
            plannedWeek?.week_start === day.date;

          const isObjectiveDate =
            day.date ===
            seasonPlan?.target_date;
          const isToday = day.date === today;
          const isSelected = day.date === selectedDateText;

          const completedDuration =
            day.activities.reduce(
              (total, activity) =>
                total +
                (
                  activity.duration_minutes ??
                  0
                ),
              0,
            );

          const completedTss =
            day.activities.reduce(
              (total, activity) =>
                total +
                (activity.tss ?? 0),
              0,
            );

          return (
            <article
              key={day.date}
              className={[
                "calendar-day",
                `calendar-day--${day.status}`,
                view === "month" &&
                !isSameMonth(
                  date,
                  selectedDate,
                )
                  ? "calendar-day--outside"
                  : "",
                isToday ? "calendar-day--today" : "",
                isSelected ? "calendar-day--selected" : "",
              ].join(" ")}
            >
              <button
                className="calendar-day__date"
                type="button"
                onClick={() =>
                  openDay(day.date)
                }
              >
                <span>
                  {view === "day"
                    ? format(
                        date,
                        "EEEE d 'de' MMMM",
                        {
                          locale: es,
                        },
                      )
                    : format(date, "d")}
                </span>

                {!(
                  view === "month" &&
                  day.status === "provisional" &&
                  !isWeekStart
                ) && (
                  <small>
                    {statusLabels[day.status]}
                  </small>
                )}                
              </button>

              {isObjectiveDate && (
                <div className="calendar-day__objective">
                  Carrera objetivo
                </div>
              )}

              {view === "month" &&
                isWeekStart &&
                plannedWeek !== null && (
                  <div
                    className={[
                      "calendar-day__week-plan",
                      `calendar-day__week-plan--${plannedWeek.phase.toLowerCase()}`,
                    ].join(" ")}
                  >
                    <strong>
                      {phaseLabels[plannedWeek.phase as keyof typeof phaseLabels]}
                    </strong>

                    <span>
                      {(plannedWeek.adapted_target_tss ?? plannedWeek.estimated_total_tss ?? plannedWeek.provisional_target_tss).toFixed(0)}{" "}
                      TSS
                    </span>

                    <small>
                      {weekStatusLabels[plannedWeek.status as keyof typeof weekStatusLabels]}
                    </small>
                  </div>
                )}

              {view === "month" && (
                <div className="calendar-day__mobile-dots" aria-label="Información del día">
                  {workout !== null && <span className="calendar-day__dot calendar-day__dot--planned" />}
                  {day.activities.length > 0 && <span className="calendar-day__dot calendar-day__dot--completed" />}
                  {isObjectiveDate && <span className="calendar-day__dot calendar-day__dot--objective" />}
                </div>
              )}

              {workout !== null ? (
                <div className="calendar-day__workout">
                  <strong>
                    {workoutLabels[workout.workout_type as keyof typeof workoutLabels]}
                  </strong>

                  <span>
                    {workout.duration_minutes ?? "—"} min
                  </span>

                  <span>
                    {(workout.estimated_tss ?? workout.target_tss).toFixed(0)}{" "}
                    TSS
                  </span>

                  {prediction !== null && (
                    <span className="calendar-day__prediction">
                      Respuesta prevista:{" "}
                      {prediction.predicted_aerobic_decoupling?.toFixed(1) ?? "—"}%
                    </span>
                  )}
                </div>
              ) : plannedWeek?.status ===
                "PROVISIONAL" ? (
                view === "day" ? (
                  <p className="calendar-day__rest">
                    Las sesiones concretas se generarán cuando
                    esta semana pase a estar activa.
                  </p>
                ) : null
              ) : view === "day" ||
                plannedWeek?.status === "ACTIVE" ? (
                <p className="calendar-day__rest">
                  Día sin entrenamiento planificado
                </p>
              ) : null}             

              {day.activities.length > 0 && (
                <div className="calendar-day__completed">
                  <strong>
                    {day.activities.length === 1
                      ? "Actividad realizada"
                      : `${day.activities.length} actividades realizadas`}
                  </strong>

                  {view !== "day" && (
                    <span>
                      {completedDuration} min ·{" "}
                      {completedTss.toFixed(1)} TSS
                    </span>
                  )}

                  {view === "day" &&
                    day.activities.map((activity) => (
                      <div className="calendar-day__activity-link" key={activity.id}>
                        <span>
                          {activity.title} · {activity.duration_minutes} min
                          {activity.tss !== null ? ` · ${activity.tss.toFixed(0)} TSS` : ""}
                        </span>
                        {workout !== null && (
                          <button
                            type="button"
                            onClick={() => void linkActivity(
                              activity.id,
                              activity.planned_workout_id === workout.id ? null : workout.id,
                            )}
                          >
                            {activity.planned_workout_id === workout.id
                              ? "Desvincular de la sesión"
                              : "Vincular con la sesión"}
                          </button>
                        )}
                      </div>
                    ))}
                </div>
              )}

              {view === "day" && (
                <button
                  className="calendar-day__add"
                  type="button"
                  onClick={() =>
                    setShowActivityForm(
                      (currentValue) =>
                        !currentValue,
                    )
                  }
                >
                  {showActivityForm
                    ? "Cerrar formulario"
                    : "Añadir actividad realizada"}
                </button>
              )}
            </article>
          );
        })}
      </section>

      {view === "day" &&
        calendarDays[0]?.activities.length >
          0 && (
          <section className="calendar-page__activities">
            <h2>Actividades realizadas</h2>

            {calendarDays[0].activities.map(
              (activity) => (
                <CompletedActivityCard
                  key={activity.id}
                  activity={activity}
                  onRemove={removeActivity}
                />
              ),
            )}
          </section>
        )}

      {view === "day" &&
        showActivityForm && (
          <ActivityForm
            onSubmit={submitActivity}
          />
        )}
    </main>
  );
}
