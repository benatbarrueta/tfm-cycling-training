from dataclasses import dataclass
from datetime import date

@dataclass
class Activity:
    date: date
    duration_minutes: int
    average_power: float
    normalized_power: float
    intensity_factor: float | None = None
    tss: float | None = None