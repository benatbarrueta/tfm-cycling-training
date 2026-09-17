from enum import Enum

class LoadDecision(Enum):
    REDUCE = "REDUCE"
    MAINTAIN = "MAINTAIN"
    INCREASE = "INCREASE"