import type {
  ActivityInput,
  Workout,
  WorkoutResponsePrediction,
} from "./training";

export type CalendarView =
  | "month"
  | "week"
  | "day";

export type CalendarDayStatus =
  | "rest"
  | "planned"
  | "completed"
  | "partial"
  | "missed";

export interface CalendarDay {
  date: string;
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