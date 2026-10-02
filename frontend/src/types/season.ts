import type {
  Objective,
  TrainingPlan,
} from "./training";

export type TrainingPhase =
  | "BASE"
  | "BUILD"
  | "PEAK"
  | "TAPER";

export type PlannedWeekStatus =
  | "PROVISIONAL"
  | "ACTIVE"
  | "COMPLETED"
  | "ADAPTED";

export interface PlannedWeek {
  week_start: string;
  week_end: string;
  phase: TrainingPhase;
  status: PlannedWeekStatus;
  planned_tss: number;
  completed_tss: number;
  training_plan: TrainingPlan | null;
  adaptation_reason: string | null;
}

export interface SeasonPlan {
  start_date: string;
  objective_date: string;
  objective: Objective;
  objective_name: string;
  weeks: PlannedWeek[];
}