import { useCallback, useEffect, useMemo, useState } from "react";
import { createSeasonPlan, getCurrentSeasonPlan, type SeasonPlan } from "../api/seasonPlans";
import type { ApiError } from "../api/client";
import { SeasonPlanContext, type SeasonPlanStatus } from "./seasonPlanContext";

export function SeasonPlanProvider({ children }: { children: React.ReactNode }) {
  const [plan, setPlan] = useState<SeasonPlan | null>(null);
  const [status, setStatus] = useState<SeasonPlanStatus>("loading");
  const [error, setError] = useState<string | null>(null);

  const refresh = useCallback(async () => {
    setStatus("loading");
    try {
      setPlan(await getCurrentSeasonPlan());
      setStatus("ready");
      setError(null);
    } catch (cause) {
      const apiError = cause as ApiError;
      if (apiError.status === 404) {
        setPlan(null);
        setStatus("missing");
        setError(null);
      } else {
        setStatus("error");
        setError(apiError.message);
      }
    }
  }, []);

  const create = useCallback(async (name: string) => {
    const created = await createSeasonPlan(name);
    setPlan(created);
    setStatus("ready");
    setError(null);
    return created;
  }, []);

  useEffect(() => {
    let active = true;
    void getCurrentSeasonPlan()
      .then((value) => {
        if (!active) return;
        setPlan(value);
        setStatus("ready");
      })
      .catch((cause: unknown) => {
        if (!active) return;
        const apiError = cause as ApiError;
        if (apiError.status === 404) {
          setPlan(null);
          setStatus("missing");
          return;
        }
        setStatus("error");
        setError(apiError.message);
      });
    return () => {
      active = false;
    };
  }, []);

  const value = useMemo(
    () => ({ plan, status, error, refresh, create }),
    [create, error, plan, refresh, status],
  );
  return <SeasonPlanContext.Provider value={value}>{children}</SeasonPlanContext.Provider>;
}
