import { useCallback, useEffect, useMemo, useState } from "react";
import { advanceCurrentSeasonPlan, createSeasonPlan, getCurrentSeasonPlan, type SeasonPlan } from "../api/seasonPlans";
import type { ApiError } from "../api/client";
import { SeasonPlanContext, type SeasonPlanStatus } from "./seasonPlanContext";
import { getSimulatedDate } from "../lib/temporal";

export function SeasonPlanProvider({ children }: { children: React.ReactNode }) {
  const [plan, setPlan] = useState<SeasonPlan | null>(null);
  const [status, setStatus] = useState<SeasonPlanStatus>("loading");
  const [error, setError] = useState<string | null>(null);

  const refresh = useCallback(async () => {
    setStatus("loading");
    try {
      setPlan(await getCurrentSeasonPlan(getSimulatedDate()));
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

  const advance = useCallback(async (referenceDate?: string | null) => {
    const result = await advanceCurrentSeasonPlan(referenceDate);
    if (result.active_week === null && result.status === "COMPLETED") {
      setPlan((current) => current === null ? null : {
        ...current,
        status: "COMPLETED",
        weeks: current.weeks.map((week) =>
          week.id === result.completed_week.id ? result.completed_week : week,
        ),
      });
    } else {
      setPlan(await getCurrentSeasonPlan(getSimulatedDate()));
    }
    setStatus("ready");
    setError(null);
    return result;
  }, []);

  useEffect(() => {
    let active = true;
    void getCurrentSeasonPlan(getSimulatedDate())
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
    () => ({ plan, status, error, refresh, create, advance }),
    [advance, create, error, plan, refresh, status],
  );
  return <SeasonPlanContext.Provider value={value}>{children}</SeasonPlanContext.Provider>;
}
