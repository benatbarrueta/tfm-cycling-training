import { useCallback, useEffect, useState } from "react";
import {
  createActivity,
  deleteActivity,
  listActivities,
  updateActivity,
  type Activity,
  type ActivityFilters,
  type ActivityInput,
} from "../api/activities";

const emptyFilters: ActivityFilters = {};

export function useActivities(filters: ActivityFilters = emptyFilters) {
  const { end, limit, offset, start } = filters;
  const [activities, setActivities] = useState<Activity[]>([]);
  const [total, setTotal] = useState(0);
  const [status, setStatus] = useState<"loading" | "ready" | "empty" | "error">("loading");
  const [error, setError] = useState<string | null>(null);

  const refresh = useCallback(async () => {
    setStatus("loading");
    try {
      const response = await listActivities({ end, limit, offset, start });
      setActivities(response.items);
      setTotal(response.total);
      setError(null);
      setStatus(response.items.length === 0 ? "empty" : "ready");
    } catch (cause) {
      const message = cause instanceof Error ? cause.message : "No se han podido cargar las actividades.";
      setError(message);
      setStatus("error");
    }
  }, [end, limit, offset, start]);

  useEffect(() => {
    let active = true;
    listActivities({ end, limit, offset, start })
      .then((response) => {
        if (!active) return;
        setActivities(response.items);
        setTotal(response.total);
        setError(null);
        setStatus(response.items.length === 0 ? "empty" : "ready");
      })
      .catch((cause: unknown) => {
        if (!active) return;
        setError(cause instanceof Error ? cause.message : "No se han podido cargar las actividades.");
        setStatus("error");
      });
    return () => {
      active = false;
    };
  }, [end, limit, offset, start]);

  const addActivity = useCallback(async (input: ActivityInput) => {
    const activity = await createActivity(input);
    setActivities((current) => [activity, ...current]);
    setTotal((current) => current + 1);
    setStatus("ready");
    return activity;
  }, []);

  const editActivity = useCallback(async (id: string, input: ActivityInput) => {
    const activity = await updateActivity(id, input);
    setActivities((current) => current.map((item) => item.id === id ? activity : item));
    return activity;
  }, []);

  const removeActivity = useCallback(async (id: string) => {
    await deleteActivity(id);
    setActivities((current) => current.filter((item) => item.id !== id));
    setTotal((current) => Math.max(0, current - 1));
  }, []);

  return { activities, total, status, error, refresh, addActivity, editActivity, removeActivity };
}
