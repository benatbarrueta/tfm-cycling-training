import type { Activity } from "../api/activities";
import type { PlannedWeek, PlannedWorkout } from "../api/seasonPlans";

export type CalendarView =
  | "month"
  | "week"
  | "day";

export type CalendarDayStatus =
  | "rest"
  | "planned"
  | "provisional"
  | "completed"
  | "partial"
  | "missed";

export interface CalendarDay {
  date: string;
  planned_week: PlannedWeek | null;
  planned_workout: PlannedWorkout | null;
  activities: ActivityRecord[];
  response_prediction: PlannedWorkout | null;
  status: CalendarDayStatus;
}

export type ActivityRecord = Activity;