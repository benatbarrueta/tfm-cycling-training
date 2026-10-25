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
  review: WeeklyReview | null;
}

export interface WeeklyReview {
  id: string;
  planned_tss: number;
  registered_tss: number;
  tss_coverage: number;
  planned_duration_minutes: number;
  registered_duration_minutes: number;
  planned_workout_count: number;
  completed_workout_count: number;
  activity_count: number;
  activities_with_tss: number;
  activities_without_tss: number;
  response_median: number | null;
  response_count: number;
  load_decision: string | null;
  decision_reason: string | null;
  closed_at: string;
}

export interface AdaptationEvent {
  id: string;
  source_week_id: string;
  target_week_id: string | null;
  previous_target_tss: number;
  provisional_target_tss: number | null;
  adapted_target_tss: number | null;
  load_decision: string | null;
  observed_aerobic_decoupling: number | null;
  response_classification: string;
  reason: string;
  rule_version: string;
  created_at: string;
}

export interface AdvanceSeasonPlanResponse {
  status: string;
  already_processed: boolean;
  completed_week: PlannedWeek;
  adaptation: AdaptationEvent;
  active_week: PlannedWeek | null;
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

export function advanceCurrentSeasonPlan() {
  return apiRequest<AdvanceSeasonPlanResponse>("/api/season-plans/current/advance", {
    method: "POST",
  });
}

export function recalculateWeekReview(weekId: string) {
  return apiRequest<WeeklyReview>(
    `/api/season-plans/current/weeks/${weekId}/review/recalculate`,
    { method: "POST" },
  );
}
