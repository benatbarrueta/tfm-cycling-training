import { apiRequest } from "./client";

export interface ExternalConnection {
  provider: "STRAVA";
  configured: boolean;
  connected: boolean;
  status: "CONNECTED" | "REAUTHORIZATION_REQUIRED" | "REVOKED" | null;
  external_display_name: string | null;
  connected_at: string | null;
  last_sync_at: string | null;
  sync_start_date: string | null;
  sync_enabled: boolean;
  sync_status: string;
  sync_total: number;
  sync_imported: number;
  sync_skipped: number;
  sync_failed: number;
  sync_last_error: string | null;
}

export function getIntegrations() {
  return apiRequest<{ items: ExternalConnection[] }>("/api/integrations");
}

export function beginStravaConnection() {
  return apiRequest<{ authorization_url: string }>("/api/integrations/strava/connect", {
    method: "POST",
  });
}

export function disconnectStrava() {
  return apiRequest<void>("/api/integrations/strava", { method: "DELETE" });
}

export interface StravaActivityCandidate {
  external_id: string;
  name: string;
  sport_type: string;
  started_at: string;
  duration_minutes: number;
  distance_km: number | null;
  elevation_gain_m: number | null;
  average_power: number | null;
  normalized_power: number | null;
  average_heart_rate: number | null;
  trainer: boolean;
  commute: boolean;
  already_imported: boolean;
}

export interface StravaActivityList {
  items: StravaActivityCandidate[];
  page: number;
  limit: number;
  has_more: boolean;
}

export function getStravaActivities({
  start,
  end,
  page = 1,
  limit = 20,
}: {
  start: string;
  end: string;
  page?: number;
  limit?: number;
}) {
  const query = new URLSearchParams({
    start,
    end,
    page: String(page),
    limit: String(limit),
  });
  return apiRequest<StravaActivityList>(`/api/integrations/strava/activities?${query}`);
}

export interface StravaSyncResult {
  status: "COMPLETED" | "COMPLETED_WITH_ERRORS" | "FAILED";
  total: number;
  imported: number;
  skipped: number;
  failed: number;
  start_date: string;
  last_error: string | null;
}

export function startStravaSync(startDate: string) {
  return apiRequest<StravaSyncResult>("/api/integrations/strava/sync", {
    method: "POST",
    body: JSON.stringify({ start_date: startDate }),
  });
}
