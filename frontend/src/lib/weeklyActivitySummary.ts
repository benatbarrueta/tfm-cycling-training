import type { Activity } from "../api/activities";
import { formatInTimeZone } from "./timezone";

export interface WeeklyActivitySummary {
  activityCount: number;
  durationMinutes: number;
  knownTss: number;
  activitiesWithTss: number;
  activitiesWithoutTss: number;
  averageAerobicDecoupling: number | null;
}

export function summarizeWeeklyActivities(
  activities: Activity[],
  weekStart: string,
  weekEnd: string,
  timezone: string,
): WeeklyActivitySummary {
  const included = activities.filter((activity) => {
    const localDate = formatInTimeZone(activity.started_at, timezone);
    return localDate >= weekStart && localDate <= weekEnd;
  });
  const decouplings = included
    .map((activity) => activity.aerobic_decoupling)
    .filter((value): value is number => value !== null);

  return {
    activityCount: included.length,
    durationMinutes: included.reduce(
      (total, activity) => total + activity.duration_minutes,
      0,
    ),
    knownTss: included.reduce(
      (total, activity) => total + (activity.tss ?? 0),
      0,
    ),
    activitiesWithTss: included.filter((activity) => activity.tss !== null).length,
    activitiesWithoutTss: included.filter((activity) => activity.tss === null).length,
    averageAerobicDecoupling:
      decouplings.length === 0
        ? null
        : decouplings.reduce((total, value) => total + value, 0) /
          decouplings.length,
  };
}
