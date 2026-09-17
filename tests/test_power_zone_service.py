from app.models.power_zone import PowerZone
from app.models.workout import WorkoutType
from app.services.power_zone_service import (
    calculate_power_range,
    get_power_zone,
)


def test_calculate_threshold_power_range():
    result = calculate_power_range(
        ftp=250,
        zone=PowerZone.Z4_THRESHOLD,
    )

    assert result == (227.5, 262.5)


def test_calculate_vo2max_power_range():
    result = calculate_power_range(
        ftp=250,
        zone=PowerZone.Z5_VO2MAX,
    )

    assert result == (265.0, 300.0)


def test_get_power_zone_from_workout_type():
    result = get_power_zone(
        WorkoutType.ENDURANCE
    )

    assert result == PowerZone.Z2_ENDURANCE