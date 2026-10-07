import { useContext } from "react";
import { SeasonPlanContext } from "../context/seasonPlanContext";

export function useSeasonPlan() {
  const context = useContext(SeasonPlanContext);
  if (context === null) {
    throw new Error("useSeasonPlan must be used inside SeasonPlanProvider");
  }
  return context;
}
