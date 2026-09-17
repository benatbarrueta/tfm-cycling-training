from dataclasses import dataclass
from enum import Enum

class LoadTrend(Enum):
    DECREASING = "DECREASING"
    STABLE = "STABLE"
    INCREASING = "INCREASING"

@dataclass
class TrainingState:
    weekly_tss: float
    previous_week_tss: float
    load_trend: LoadTrend
    training_frequency: int