import { apiRequest } from "./client";
import type { CyclistFormValues } from "../schemas/cyclistSchema";

export interface CyclistProfile {
  id: string;
  user_id: string;
  ftp: number;
  weekly_hours: number;
  available_days: CyclistFormValues["available_days"];
  modality: CyclistFormValues["modality"];
  level: CyclistFormValues["level"];
  objective: CyclistFormValues["objective"];
  target_date: string | null;
  timezone: string;
  onboarding_completed_at: string;
  created_at: string;
  updated_at: string;
}

export function getCyclistProfile() {
  return apiRequest<CyclistProfile>("/api/profile");
}

export function saveCyclistProfile(values: CyclistFormValues) {
  return apiRequest<CyclistProfile>("/api/profile", {
    method: "PUT",
    body: JSON.stringify({
      ...values,
      target_date: values.objective_date,
      timezone: "Europe/Madrid",
    }),
  });
}
