import { useCallback, useState } from "react";
import {
  getStravaActivities,
  startStravaSync,
  type StravaActivityCandidate,
  type StravaSyncResult,
} from "../api/integrations";

export type StravaSyncPreview = {
  total: number;
  importable: number;
  duplicates: number;
  durationMinutes: number;
  distanceKm: number;
};

const emptyPreview: StravaSyncPreview = {
  total: 0,
  importable: 0,
  duplicates: 0,
  durationMinutes: 0,
  distanceKm: 0,
};

export function useStravaActivities() {
  const [preview, setPreview] = useState<StravaSyncPreview>(emptyPreview);
  const [status, setStatus] = useState<"idle" | "loading" | "ready" | "empty" | "error">("idle");
  const [error, setError] = useState<string | null>(null);
  const [syncResult, setSyncResult] = useState<StravaSyncResult | null>(null);

  const loadPreview = useCallback(async ({ start, end }: { start: string; end: string }) => {
    setStatus("loading");
    setError(null);
    try {
      const activities: StravaActivityCandidate[] = [];
      let page = 1;
      let hasMore = true;
      while (hasMore) {
        const response = await getStravaActivities({ start, end, page, limit: 100 });
        activities.push(...response.items);
        hasMore = response.has_more;
        page += 1;
        if (page > 100) throw new Error("El intervalo contiene demasiadas actividades. Elige una fecha más reciente.");
      }

      const duplicates = activities.filter((activity) => activity.already_imported).length;
      setPreview({
        total: activities.length,
        importable: activities.length - duplicates,
        duplicates,
        durationMinutes: activities.reduce((total, activity) => total + activity.duration_minutes, 0),
        distanceKm: activities.reduce((total, activity) => total + (activity.distance_km ?? 0), 0),
      });
      setStatus(activities.length === 0 ? "empty" : "ready");
    } catch (cause) {
      setPreview(emptyPreview);
      setStatus("error");
      setError(cause instanceof Error ? cause.message : "No se han podido consultar las actividades de Strava.");
    }
  }, []);

  const synchronize = useCallback(async (startDate: string) => {
    setStatus("loading");
    setError(null);
    setSyncResult(null);
    try {
      const result = await startStravaSync(startDate);
      setSyncResult(result);
      setStatus("ready");
      return result;
    } catch (cause) {
      setStatus("error");
      setError(cause instanceof Error ? cause.message : "No se ha podido sincronizar con Strava.");
      return null;
    }
  }, []);

  return { preview, status, error, syncResult, loadPreview, synchronize };
}
