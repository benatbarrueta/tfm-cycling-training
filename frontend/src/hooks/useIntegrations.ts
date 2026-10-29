import { useCallback, useEffect, useState } from "react";
import {
  beginStravaConnection,
  disconnectStrava,
  getIntegrations,
  type ExternalConnection,
} from "../api/integrations";

export function useIntegrations() {
  const [strava, setStrava] = useState<ExternalConnection | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const applyResponse = useCallback((response: Awaited<ReturnType<typeof getIntegrations>>) => {
    setStrava(response.items.find((item) => item.provider === "STRAVA") ?? null);
    setError(null);
  }, []);

  const refresh = useCallback(async () => {
    setLoading(true);
    try {
      const response = await getIntegrations();
      applyResponse(response);
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : "No se han podido cargar las conexiones.");
    } finally {
      setLoading(false);
    }
  }, [applyResponse]);

  useEffect(() => {
    let active = true;
    getIntegrations()
      .then((response) => {
        if (active) applyResponse(response);
      })
      .catch((cause) => {
        if (active) setError(cause instanceof Error ? cause.message : "No se han podido cargar las conexiones.");
      })
      .finally(() => {
        if (active) setLoading(false);
      });
    return () => {
      active = false;
    };
  }, [applyResponse]);

  const connect = useCallback(async () => {
    const response = await beginStravaConnection();
    window.location.assign(response.authorization_url);
  }, []);

  const disconnect = useCallback(async () => {
    await disconnectStrava();
    await refresh();
  }, [refresh]);

  return { strava, loading, error, connect, disconnect, refresh };
}
