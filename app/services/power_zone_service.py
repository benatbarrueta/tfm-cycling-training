from app.config.power_zones import POWER_ZONE_PERCENTAGES
from app.models.power_zone import PowerZone
from app.models.workout import WorkoutType


ZONE_PERCENTAGES = {
    PowerZone.Z1_RECOVERY: (0.0, 0.55),
    PowerZone.Z2_ENDURANCE: (0.56, 0.75),
    PowerZone.Z3_TEMPO: (0.76, 0.90),
    PowerZone.Z4_THRESHOLD: (0.91, 1.05),
    PowerZone.Z5_VO2MAX: (1.06, 1.20),
}

WORKOUT_POWER_ZONES = {
    WorkoutType.RECOVERY: PowerZone.Z1_RECOVERY,
    WorkoutType.ENDURANCE: PowerZone.Z2_ENDURANCE,
    WorkoutType.TEMPO: PowerZone.Z3_TEMPO,
    WorkoutType.THRESHOLD: PowerZone.Z4_THRESHOLD,
    WorkoutType.VO2MAX: PowerZone.Z5_VO2MAX,
}

def get_power_zone(
    workout_type: WorkoutType,
) -> PowerZone:
    return WORKOUT_POWER_ZONES[workout_type]


def calculate_power_range(
    ftp: float,
    zone: PowerZone,
) -> tuple[float, float]:
    """
    Calculate the power range for a given power zone and FTP.

    Args:
        ftp (float): Functional Threshold Power.
        zone (PowerZone): The power zone for which to calculate the range.
    
    Returns:
        tuple[float, float]: A tuple containing the minimum and maximum power for the specified zone
    """
    if ftp <= 0:
        raise ValueError("FTP must be greater than 0")

    min_percentage, max_percentage = (
        POWER_ZONE_PERCENTAGES[zone]
    )

    return (
        round(ftp * min_percentage, 2),
        round(ftp * max_percentage, 2),
    )