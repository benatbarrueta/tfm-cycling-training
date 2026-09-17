from app.models.training_state import LoadTrend
from app.models.activity import Activity

def calculate_if(normalized_power: float, ftp: float) -> float:
    """
    Calculate the Intensity Factor (IF) based on normalized power and threshold power.

    Args:
        normalized_power (float): The normalized power of the cyclist.
        threshold_power (float): The threshold power of the cyclist.

    Returns:
        float: The calculated Intensity Factor (IF).
    """
    if ftp == 0:
        raise ValueError("Threshold power cannot be zero.")
    
    return normalized_power / ftp

def calculate_tss(
    duration_seconds: int,
    normalized_power: float,
    ftp: float
) -> float:
    """
    Calculate the Training Stress Score (TSS) based on duration, normalized power, and threshold power.

    Args:
        duration_seconds (int): The duration of the activity in seconds.
        normalized_power (float): The normalized power of the cyclist.
        threshold_power (float): The threshold power of the cyclist.

    Returns:
        float: The calculated Training Stress Score (TSS).
    """
    if ftp == 0:
        raise ValueError("Threshold power cannot be zero.")
    
    intensity_factor = calculate_if(normalized_power, ftp)
    
    return duration_seconds * normalized_power * intensity_factor * 100 / (ftp * 3600)

def calculate_weekly_tss(tss_values: list[float]) -> float:
    """
    Calculate the total Training Stress Score (TSS) for a week based on individual TSS values.

    Args:
        tss_values (list[float]): A list of individual TSS values for each activity in the week.

    Returns:
        float: The total Training Stress Score (TSS) for the week.
    """
    return sum(tss_values)

def calculate_load_trend(weekly_tss: float, previous_week_tss: float) -> LoadTrend:
    """
    Calculate the load trend based on the current week's TSS and the previous week's TSS.

    Args:
        weekly_tss (float): The total Training Stress Score (TSS) for the current week.
        previous_week_tss (float): The total Training Stress Score (TSS) for the previous week.

    Returns:
        str: The load trend, which can be "DECREASING", "STABLE", or "INCREASING".
    """
    if weekly_tss < previous_week_tss:
        return LoadTrend.DECREASING
    elif weekly_tss == previous_week_tss:
        return LoadTrend.STABLE
    else:
        return LoadTrend.INCREASING

def calculate_activity_metrics(
        activity: Activity,
        ftp: float
) -> Activity:
    """
    Calculate the Intensity Factor (IF) and Training Stress Score (TSS) for a given activity.

    Args:
        activity (Activity): The activity object containing duration, normalized power, and other metrics.
        ftp (float): The threshold power of the cyclist.

    Returns:
        Activity: The updated activity object with calculated IF and TSS values.
    """

    if ftp <= 0:
        raise ValueError("Threshold power (FTP) must be greater than zero.")

    activity.intensity_factor = calculate_if(
        normalized_power=activity.normalized_power,
        ftp=ftp
    )

    activity.tss = calculate_tss(
        duration_seconds=activity.duration_minutes * 60,
        normalized_power=activity.normalized_power,
        ftp=ftp
    )

    return activity