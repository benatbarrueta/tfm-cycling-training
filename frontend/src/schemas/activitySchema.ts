import { z } from "zod";

const optionalNumber = (
  schema: z.ZodNumber,
) =>
  z.preprocess(
    (value) =>
      value === "" || value === undefined
        ? null
        : value,
    z.coerce.number().pipe(schema).nullable(),
  );

export const activitySchema = z.object({
  date: z
    .string()
    .min(1, "Selecciona la fecha de la actividad."),

  duration_minutes: optionalNumber(
    z
      .number()
      .positive("La duración debe ser mayor que cero."),
  ),

  average_power: optionalNumber(
    z
      .number()
      .positive("La potencia media debe ser mayor que cero."),
  ),

  normalized_power: optionalNumber(
    z
      .number()
      .positive("La potencia normalizada debe ser mayor que cero."),
  ),

  intensity_factor: optionalNumber(
    z
      .number()
      .positive("El factor de intensidad debe ser mayor que cero.")
      .max(2, "El factor de intensidad parece demasiado alto."),
  ),

  tss: optionalNumber(
    z
      .number()
      .nonnegative("El TSS no puede ser negativo."),
  ),

  aerobic_decoupling: optionalNumber(
    z.number(),
  ),
}).superRefine((activity, context) => {
  const hasTrainingInformation =
    activity.tss !== null ||
    (
      activity.duration_minutes !== null &&
      activity.intensity_factor !== null
    );

  if (!hasTrainingInformation) {
    context.addIssue({
      code: "custom",
      path: ["tss"],
      message:
        "Introduce el TSS o la duración junto con el factor de intensidad.",
    });
  }
});

export type ActivityFormValues = z.infer<
  typeof activitySchema
>;

export type ActivityFormInput = z.input<
  typeof activitySchema
>;