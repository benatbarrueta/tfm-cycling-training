from dataclasses import dataclass
from datetime import date
from enum import Enum

from app.models.training_objective import Objective

class Modality(Enum):
    ROAD = "ROAD"
    XCO = "XCO"
    XCM = "XCM"

class Level(Enum):
    BEGINNER = "BEGINNER"
    INTERMEDIATE = "INTERMEDIATE"
    ADVANCED = "ADVANCED"

@dataclass
class Cyclist:
    cyclist_id: int
    modalities: list[Modality]
    level: Level
    ftp: float
    weekly_hours: float
    available_days: list[str]
    objective: Objective
    objective_date: date | None = None