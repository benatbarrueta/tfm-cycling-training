import { z } from "zod";

const optionalNumber = z.preprocess(
  (value) => value === "" || value === undefined ? null : value,
  z.coerce.number().nullable(),
);

export const activitySchema = z.object({
  title: z.string().trim().min(1, "Introduce un título."),
  started_at: z.string().min(1, "Selecciona la fecha y hora."),
  duration_minutes: z.coerce.number().positive("La duración debe ser mayor que cero."),
  distance_km: optionalNumber.refine((value) => value === null || value >= 0, "No puede ser negativa."),
  average_power: optionalNumber.refine((value) => value === null || value >= 0, "No puede ser negativa."),
  normalized_power: optionalNumber.refine((value) => value === null || value >= 0, "No puede ser negativa."),
  average_heart_rate: optionalNumber.refine((value) => value === null || value > 0, "Debe ser mayor que cero."),
  intensity_factor: optionalNumber.refine((value) => value === null || value >= 0, "No puede ser negativo."),
  tss: optionalNumber.refine((value) => value === null || value >= 0, "No puede ser negativo."),
  perceived_exertion: optionalNumber.refine(
    (value) => value === null || (Number.isInteger(value) && value >= 1 && value <= 10),
    "El esfuerzo percibido debe ser un número entero entre 1 y 10.",
  ),
  aerobic_decoupling: optionalNumber,
  notes: z.string().nullable(),
});

export type ActivityFormValues = z.infer<typeof activitySchema>;
export type ActivityFormInput = z.input<typeof activitySchema>;
