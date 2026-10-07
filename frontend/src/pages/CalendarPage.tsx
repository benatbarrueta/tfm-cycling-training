import { useMemo, useState } from "react";
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
import { phaseLabels, workoutLabels } from "../lib/labels";
import { seasonPlanMock } from "../mocks/seasonPlan";
import type {
  CalendarDay,
  CalendarView,
} from "../types/calendar";
import type { ActivityInput } from "../types/training";
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
  const seasonPlan = seasonPlanMock;

  const [view, setView] =
    useState<CalendarView>("month");

  const [selectedDate, setSelectedDate] =
    useState(() =>
      new Date(),
    );

  const [
    showActivityForm,
    setShowActivityForm,
  ] = useState(false);

  const {
    activities,
    addActivity,
    removeActivity,
  } = useActivities();

  const visibleDates = useMemo(
    () => getVisibleDates(selectedDate, view),
    [selectedDate, view],
  );

  const selectedDateText = format(
    selectedDate,
    "yyyy-MM-dd",
  );

  const selectedWeek =
    seasonPlan.weeks.find(
      (week) =>
        selectedDateText >= week.week_start &&
        selectedDateText <= week.week_end,
    ) ?? null;

  const calendarDays = useMemo<CalendarDay[]>(
    () =>
      visibleDates.map((date) => {
        const isoDate = format(
          date,
          "yyyy-MM-dd",
        );

        const plannedWeek =
          seasonPlan.weeks.find(
            (week) =>
              isoDate >= week.week_start &&
              isoDate <= week.week_end,
          ) ?? null;

        const trainingPlan =
          plannedWeek?.training_plan ?? null;

        const prediction =
          trainingPlan
            ?.workout_response_predictions
            .find(
              (item) =>
                item.session_date === isoDate,
            ) ?? null;

        const plannedWorkout =
          prediction === null
            ? null
            : trainingPlan?.workouts.find(
                (workout) =>
                  workout.day === prediction.day,
              ) ?? null;

        const dayActivities =
          activities.filter(
            (activity) =>
              activity.date === isoDate,
          );

        let status: CalendarDay["status"];

        const completedTss = dayActivities.reduce(
          (total, activity) => total + (activity.tss ?? 0),
          0,
        );
        const plannedTss = plannedWorkout?.estimated_tss ?? plannedWorkout?.target_tss ?? 0;

        if (dayActivities.length > 0 && plannedTss > 0 && completedTss < plannedTss * 0.8) {
          status = "partial";
        } else if (dayActivities.length > 0) {
          status = "completed";
        } else if (plannedWorkout !== null) {
          status = isoDate < format(new Date(), "yyyy-MM-dd") ? "missed" : "planned";
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
      visibleDates,
    ],
  );

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
    setSelectedDate(new Date());
    setShowActivityForm(false);
  }

  function changeView(
    nextView: CalendarView,
  ) {
    setView(nextView);
    setShowActivityForm(false);
  }

  function submitActivity(
    activity: ActivityInput,
  ) {
    addActivity(activity);
    setSelectedDate(parseISO(activity.date));
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

      {selectedWeek !== null && (
        <section
          className={[
            "calendar-page__week-summary",
            `calendar-page__week-summary--${selectedWeek.status.toLowerCase()}`,
          ].join(" ")}
        >
          <div>
            <span>
              {phaseLabels[selectedWeek.phase]}
            </span>

            <strong>
              Semana{" "}
              {weekStatusLabels[
                selectedWeek.status
              ].toLowerCase()}
            </strong>
          </div>

          <dl>
            <div>
              <dt>TSS previsto</dt>
              <dd>
                {selectedWeek.planned_tss.toFixed(
                  0,
                )}
              </dd>
            </div>

            <div>
              <dt>TSS realizado</dt>
              <dd>
                {selectedWeek.completed_tss.toFixed(
                  0,
                )}
              </dd>
            </div>
          </dl>

          {selectedWeek.adaptation_reason && (
            <p>
              {selectedWeek.adaptation_reason}
            </p>
          )}

          {selectedWeek.status ===
            "PROVISIONAL" && (
            <p>
              Las sesiones concretas se generarán
              cuando esta semana pase a estar activa.
            </p>
          )}
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
            seasonPlan.objective_date;
          const isToday = day.date === format(new Date(), "yyyy-MM-dd");
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
                      {phaseLabels[
                        plannedWeek.phase
                      ]}
                    </strong>

                    <span>
                      {plannedWeek.planned_tss.toFixed(
                        0,
                      )}{" "}
                      TSS
                    </span>

                    <small>
                      {weekStatusLabels[
                        plannedWeek.status
                      ]}
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
                    {workoutLabels[workout.workout_type]}
                  </strong>

                  <span>
                    {workout.duration_minutes ?? "—"} min
                  </span>

                  <span>
                    {workout.estimated_tss?.toFixed(0) ??
                      "—"}{" "}
                    TSS
                  </span>

                  {prediction !== null && (
                    <span className="calendar-day__prediction">
                      Respuesta prevista:{" "}
                      {prediction
                        .predicted_aerobic_decoupling
                        .toFixed(1)}
                      %
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
                    Actividad completada
                  </strong>

                  <span>
                    {completedDuration} min ·{" "}
                    {completedTss.toFixed(1)} TSS
                  </span>

                  {day.activities.length > 1 && (
                    <span>
                      {day.activities.length}{" "}
                      actividades
                    </span>
                  )}
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
            initialDate={format(
              selectedDate,
              "yyyy-MM-dd",
            )}
            onSubmit={submitActivity}
          />
        )}
    </main>
  );
}