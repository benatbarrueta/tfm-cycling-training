import { addDays, format, parseISO, startOfWeek } from "date-fns";
import { formatInTimeZone } from "./timezone";

export type WeekTemporalState = "UPCOMING" | "CURRENT" | "PAST";

export function getCurrentDate(): Date {
  return new Date();
}

export interface WeekRange {
  weekStart: string;
  weekEnd: string;
}

export function getCurrentWeekRange(
  referenceDate: Date | string,
  timezone: string,
): WeekRange {
  const localDate = getTodayInTimeZone(referenceDate, timezone);
  const start = startOfWeek(parseISO(localDate), { weekStartsOn: 1 });
  return {
    weekStart: format(start, "yyyy-MM-dd"),
    weekEnd: format(addDays(start, 6), "yyyy-MM-dd"),
  };
}

export function getWeekTemporalState(
  today: string,
  weekStart: string,
  weekEnd: string,
): WeekTemporalState {
  if (today < weekStart) return "UPCOMING";
  if (today > weekEnd) return "PAST";
  return "CURRENT";
}

export function getTodayInTimeZone(
  now: Date | string,
  timezone: string,
): string {
  return formatInTimeZone(now, timezone);
}

export function getWeekLabel(
  status: string,
  temporalState: WeekTemporalState,
): string {
  if (temporalState === "UPCOMING") return "Próxima semana";
  if (temporalState === "CURRENT" && status === "ACTIVE") {
    return "Semana activa";
  }
  if (status === "COMPLETED") return "Semana completada";
  if (status === "PROVISIONAL") return "Semana provisional";
  if (temporalState === "PAST") return "Semana pasada";
  return "Semana activa";
}
