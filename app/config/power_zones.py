from app.models.power_zone import PowerZone


POWER_ZONE_PERCENTAGES = {
    PowerZone.Z1_RECOVERY: (0.00, 0.55),
    PowerZone.Z2_ENDURANCE: (0.56, 0.75),
    PowerZone.Z3_TEMPO: (0.76, 0.90),
    PowerZone.Z4_THRESHOLD: (0.91, 1.05),
    PowerZone.Z5_VO2MAX: (1.06, 1.20),
}