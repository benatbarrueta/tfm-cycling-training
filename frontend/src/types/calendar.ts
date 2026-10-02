import type {
  ActivityInput,
  Workout,
  WorkoutResponsePrediction,
} from "./training";

import type {
  PlannedWeek,
} from "./season";

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
  planned_workout: Workout | null;
  activities: ActivityRecord[];
  response_prediction:
    | WorkoutResponsePrediction
    | null;
  status: CalendarDayStatus;
}

export interface ActivityRecord extends ActivityInput {
  id: string;
}