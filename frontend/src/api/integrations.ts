import { apiRequest } from "./client";

export interface ExternalConnection {
  provider: "STRAVA";
  configured: boolean;
  connected: boolean;
  status: "CONNECTED" | "REAUTHORIZATION_REQUIRED" | "REVOKED" | null;
  external_display_name: string | null;
  connected_at: string | null;
  last_sync_at: string | null;
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
