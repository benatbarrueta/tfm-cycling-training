import { apiRequest } from "./client";

export interface Activity {
  id: string;
  planned_workout_id: string | null;
  title: string;
  started_at: string;
  sport: "CYCLING";
  duration_minutes: number;
  distance_km: number | null;
  average_power: number | null;
  normalized_power: number | null;
  average_heart_rate: number | null;
  intensity_factor: number | null;
  tss: number | null;
  aerobic_decoupling: number | null;
  source: string;
  notes: string | null;
  created_at: string;
  updated_at: string;
}

export type ActivityInput = Omit<
  Activity,
  "id" | "planned_workout_id" | "source" | "created_at" | "updated_at"
>;

export interface ActivityListResponse {
  items: Activity[];
  total: number;
  limit: number;
  offset: number;
}

export interface ActivityFilters {
  start?: string;
  end?: string;
  limit?: number;
  offset?: number;
}

export function listActivities(filters: ActivityFilters = {}) {
  const params = new URLSearchParams();
  Object.entries(filters).forEach(([key, value]) => {
    if (value !== undefined) params.set(key, String(value));
  });
  const query = params.toString();
  return apiRequest<ActivityListResponse>(`/api/activities${query ? `?${query}` : ""}`);
}

export function getActivity(id: string) {
  return apiRequest<Activity>(`/api/activities/${id}`);
}

export function createActivity(input: ActivityInput) {
  return apiRequest<Activity>("/api/activities", {
    method: "POST",
    body: JSON.stringify(input),
  });
}

export function updateActivity(id: string, input: ActivityInput) {
  return apiRequest<Activity>(`/api/activities/${id}`, {
    method: "PUT",
    body: JSON.stringify(input),
  });
}

export function deleteActivity(id: string) {
  return apiRequest<void>(`/api/activities/${id}`, { method: "DELETE" });
}

export function linkActivityToWorkout(id: string, plannedWorkoutId: string | null) {
  return apiRequest<Activity>(`/api/activities/${id}/planned-workout`, {
    method: "PUT",
    body: JSON.stringify({ planned_workout_id: plannedWorkoutId }),
  });
}
