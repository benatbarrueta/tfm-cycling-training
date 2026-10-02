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
import {CompletedActivityCard,} from "../components/CompletedActivityCard";
import { useActivities } from "../hooks/useActivities";
import { trainingPlanMock } from "../mocks/trainingPlan";
import type {
  CalendarDay,
  CalendarView,
} from "../types/calendar";
import type { ActivityInput } from "../types/training";
import "../styles/CalendarPage.css";

const statusLabels = {
  rest: "Descanso",
  planned: "Planificado",
  completed: "Completado",
  partial: "Parcial",
  missed: "No realizado",
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
  const planResponse = trainingPlanMock;

  const [view, setView] =
    useState<CalendarView>("week");

  const [selectedDate, setSelectedDate] =
    useState(() =>
      parseISO(planResponse.reference_date),
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

  const calendarDays = useMemo<CalendarDay[]>(
    () =>
      visibleDates.map((date) => {
        const isoDate = format(
          date,
          "yyyy-MM-dd",
        );

        const prediction =
          planResponse.plan
            .workout_response_predictions
            .find(
              (item) =>
                item.session_date === isoDate,
            ) ?? null;

        const plannedWorkout =
          prediction === null
            ? null
            : planResponse.plan.workouts.find(
                (workout) =>
                  workout.day === prediction.day,
              ) ?? null;

        const dayActivities = activities.filter(
          (activity) =>
            activity.date === isoDate,
        );

        let status: CalendarDay["status"];

        if (dayActivities.length > 0) {
          status = "completed";
        } else if (plannedWorkout !== null) {
          status = "planned";
        } else {
          status = "rest";
        }

        return {
          date: isoDate,
          planned_workout: plannedWorkout,
          activities: dayActivities,
          response_prediction: prediction,
          status,
        };
      }),
    [
      activities,
      planResponse,
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
            <span key={day}>
              {day}
            </span>
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
          const workout =
            day.planned_workout;
          const prediction =
            day.response_prediction;

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
                total + (activity.tss ?? 0),
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

                <small>
                  {statusLabels[day.status]}
                </small>
              </button>

              {workout !== null ? (
                <div className="calendar-day__workout">
                  <strong>
                    {workout.workout_type}
                  </strong>

                  <span>
                    {workout.duration_minutes ??
                      "—"}{" "}
                    min
                  </span>

                  <span>
                    {workout.estimated_tss
                      ?.toFixed(0) ?? "—"}{" "}
                    TSS
                  </span>

                  {prediction !== null && (
                    <span>
                      Respuesta prevista:{" "}
                      {prediction
                        .predicted_aerobic_decoupling
                        .toFixed(1)}
                      %
                    </span>
                  )}
                </div>
              ) : (
                <p className="calendar-day__rest">
                  Día sin entrenamiento
                  planificado
                </p>
              )}

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
        calendarDays[0]?.activities.length > 0 && (
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