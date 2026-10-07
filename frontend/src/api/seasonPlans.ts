import { apiRequest } from "./client";
import type { IntervalBlock, SessionPhase } from "../types/training";

export interface PlannedWorkout {
  id: string;
  position: number;
  scheduled_date: string;
  day: string;
  workout_type: string;
  target_tss: number;
  estimated_tss: number | null;
  duration_minutes: number | null;
  target_power_min: number | null;
  target_power_max: number | null;
  warmup: SessionPhase | null;
  intervals: IntervalBlock | null;
  cooldown: SessionPhase | null;
  predicted_aerobic_decoupling: number | null;
  aerobic_response: string | null;
  outside_training_range_features: string[] | null;
}

export interface PlannedWeek {
  id: string;
  position: number;
  week_start: string;
  week_end: string;
  status: string;
  focus: string;
  phase: string;
  provisional_target_tss: number;
  provisional_hours: number;
  requested_target_tss: number | null;
  adapted_target_tss: number | null;
  estimated_total_tss: number | null;
  expected_aerobic_decoupling: number | null;
  response_prediction_method: string | null;
  load_decision: string | null;
  generated_at: string | null;
  workouts: PlannedWorkout[];
}

export interface SeasonPlan {
  id: string;
  name: string;
  status: string;
  start_date: string;
  target_date: string;
  objective: string;
  modality: string;
  level: string;
  ftp_snapshot: number;
  weekly_hours_snapshot: number;
  available_days_snapshot: string[];
  generator_version: string;
  created_at: string;
  updated_at: string;
  phases: { id: string; phase_type: string; position: number; start_date: string; end_date: string; week_count: number }[];
  weeks: PlannedWeek[];
}

export function getCurrentSeasonPlan() {
  return apiRequest<SeasonPlan>("/api/season-plans/current");
}

export function createSeasonPlan(name: string) {
  return apiRequest<SeasonPlan>("/api/season-plans", {
    method: "POST",
    body: JSON.stringify({ name }),
  });
}
