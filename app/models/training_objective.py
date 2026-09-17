from enum import Enum


class Objective(Enum):
    ENDURANCE = "ENDURANCE"
    PERFORMANCE = "PERFORMANCE"
    RACE = "RACE"


class RacePhase(Enum):
    BASE = "BASE"
    BUILD = "BUILD"
    PEAK = "PEAK"
    TAPER = "TAPER"