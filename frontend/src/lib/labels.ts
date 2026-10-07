import type {
  AerobicResponse,
  LoadDecision,
  WeekDay,
  WorkoutType,
} from "../types/training";
import type { PlannedWeekStatus, TrainingPhase } from "../types/season";

export const dayLabels: Record<WeekDay, string> = {
  MONDAY: "Lunes",
  TUESDAY: "Martes",
  WEDNESDAY: "Miércoles",
  THURSDAY: "Jueves",
  FRIDAY: "Viernes",
  SATURDAY: "Sábado",
  SUNDAY: "Domingo",
};

export const workoutLabels: Record<WorkoutType, string> = {
  RECOVERY: "Recuperación",
  ENDURANCE: "Resistencia",
  TEMPO: "Tempo",
  THRESHOLD: "Umbral",
  VO2MAX: "VO₂ máx.",
};

export const responseLabels: Record<AerobicResponse, string> = {
  UNKNOWN: "Datos insuficientes",
  STABLE: "Respuesta estable",
  ELEVATED: "Respuesta elevada",
};

export const decisionLabels: Record<LoadDecision, string> = {
  INCREASE: "Progresar",
  MAINTAIN: "Mantener carga",
  REDUCE: "Reducir carga",
};

export const phaseLabels: Record<TrainingPhase, string> = {
  BASE: "Base",
  BUILD: "Construcción",
  PEAK: "Pico",
  TAPER: "Descarga",
};

export const weekStatusLabels: Record<PlannedWeekStatus, string> = {
  PROVISIONAL: "Provisional",
  ACTIVE: "Semana activa",
  COMPLETED: "Completada",
  ADAPTED: "Adaptada",
};
