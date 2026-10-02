import { z } from "zod";

export const modalityOptions = [
  "ROAD",
  "XCO",
  "XCM",
] as const;

export const levelOptions = [
  "BEGINNER",
  "INTERMEDIATE",
  "ADVANCED",
] as const;

export const objectiveOptions = [
  "ENDURANCE",
  "PERFORMANCE",
  "RACE",
] as const;

export const weekDayOptions = [
  "MONDAY",
  "TUESDAY",
  "WEDNESDAY",
  "THURSDAY",
  "FRIDAY",
  "SATURDAY",
  "SUNDAY",
] as const;

export const cyclistSchema = z.object({
  ftp: z.coerce
    .number()
    .positive("El FTP debe ser mayor que cero.")
    .max(600, "Comprueba el valor del FTP."),

  weekly_hours: z.coerce
    .number()
    .positive(
      "Las horas disponibles deben ser mayores que cero.",
    )
    .max(
      40,
      "Comprueba las horas semanales.",
    ),

  modality: z.enum(modalityOptions),

  level: z.enum(levelOptions),

  objective: z.enum(objectiveOptions),

  objective_date: z
    .union([
        z.string(),
        z.null(),
    ])
    .transform((value) =>
        value === "" ? null : value,
    ),

  available_days: z
    .array(z.enum(weekDayOptions))
    .min(
      1,
      "Selecciona al menos un día disponible.",
    ),
});

export type CyclistFormValues = z.infer<
  typeof cyclistSchema
>;

export type CyclistFormInput = z.input<
  typeof cyclistSchema
>;