import { createContext } from "react";
import type { AdvanceSeasonPlanResponse, SeasonPlan } from "../api/seasonPlans";

export type SeasonPlanStatus = "loading" | "missing" | "ready" | "error";

export interface SeasonPlanContextValue {
  plan: SeasonPlan | null;
  status: SeasonPlanStatus;
  error: string | null;
  refresh: () => Promise<void>;
  create: (name: string) => Promise<SeasonPlan>;
  advance: (referenceDate?: string | null) => Promise<AdvanceSeasonPlanResponse>;
}

export const SeasonPlanContext = createContext<SeasonPlanContextValue | null>(null);
