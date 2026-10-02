export type Modality = "ROAD" | "XCO" | "XCM";

export type Level =
  | "BEGINNER"
  | "INTERMEDIATE"
  | "ADVANCED";

export type Objective =
  | "ENDURANCE"
  | "PERFORMANCE"
  | "RACE";

export type WeekDay =
  | "MONDAY"
  | "TUESDAY"
  | "WEDNESDAY"
  | "THURSDAY"
  | "FRIDAY"
  | "SATURDAY"
  | "SUNDAY";

export type WorkoutType =
  | "RECOVERY"
  | "ENDURANCE"
  | "TEMPO"
  | "THRESHOLD"
  | "VO2MAX";

export type AerobicResponse =
  | "UNKNOWN"
  | "STABLE"
  | "ELEVATED";

export type LoadDecision =
  | "INCREASE"
  | "MAINTAIN"
  | "REDUCE";

export interface CyclistInput {
  ftp: number;
  weekly_hours: number;
  available_days: WeekDay[];
  modality: Modality;
  level: Level;
  objective: Objective;
  objective_date: string | null;
}

export interface ActivityInput {
  date: string;
  duration_minutes: number | null;
  average_power: number | null;
  normalized_power: number | null;
  intensity_factor: number | null;
  tss: number | null;
  aerobic_decoupling: number | null;
}

export interface TrainingPlanRequest {
  cyclist: CyclistInput;
  activities: ActivityInput[];
  reference_date: string | null;
}

export interface SessionPhase {
  duration_minutes: number;
  target_power_min: number | null;
  target_power_max: number | null;
}

export interface IntervalBlock {
  repetitions: number;
  work_minutes: number;
  recovery_minutes: number;
  work_power_min: number;
  work_power_max: number;
  recovery_power_min: number;
  recovery_power_max: number;
}

export interface Workout {
  day: WeekDay;
  workout_type: WorkoutType;
  target_tss: number;
  estimated_tss: number | null;
  duration_minutes: number | null;
  target_power_min: number | null;
  target_power_max: number | null;
  warmup: SessionPhase | null;
  intervals: IntervalBlock | null;
  cooldown: SessionPhase | null;
}

export interface WorkoutResponsePrediction {
  day: WeekDay;
  session_date: string;
  predicted_aerobic_decoupling: number;
  aerobic_response: AerobicResponse;
  outside_training_range_features: string[];
}

export interface TrainingPlan {
  requested_target_tss: number | null;
  target_tss: number;
  feasibility_adjusted: boolean;
  estimated_total_tss: number;
  estimated_tss_difference: number;
  total_duration_minutes: number;
  expected_aerobic_decoupling: number | null;
  response_prediction_method: string;
  response_evaluated_target_tss: number | null;
  workout_response_predictions: WorkoutResponsePrediction[];
  aerobic_response: AerobicResponse;
  load_decision: LoadDecision | null;
  workouts: Workout[];
}

export interface SourceAudit {
  athlete_id: string;
  source_activities: number;
  imported_activities: number;
  skipped_non_bike: number;
  skipped_invalid: number;
  duplicate_activities: number;
  eligible_calculated_responses?: number;
  source?: string;
}

export interface TrainingPlanResponse {
  source_audit?: SourceAudit;
  reference_date: string;
  response_model?: string;
  plan: TrainingPlan;
}