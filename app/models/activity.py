from dataclasses import dataclass
from datetime import date


@dataclass
class Activity:
    date: date
    duration_minutes: int | None
    average_power: float | None
    normalized_power: float | None
    intensity_factor: float | None = None
    tss: float | None = None
    aerobic_decoupling: float | None = None