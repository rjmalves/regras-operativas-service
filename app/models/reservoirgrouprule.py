from pydantic import BaseModel
from typing import Optional, List


class ReservoirGroupRule(BaseModel):
    """
    Class for defining a reservoir operation rule
    based on other states.
    """

    reservoirCodes: List[int]
    uheCode: int
    constraintType: str
    month: int
    minVolume: float
    maxVolume: float
    minLimit: Optional[float]
    maxLimit: Optional[float]
    frequency: str
    label: Optional[str]

    def __str__(self) -> str:
        return (
            f"Regra: reservatórios {self.reservoirCodes}"
            + f" -> usina {self.uheCode} | {self.constraintType}"
            + f" mês {self.month}. Faixa {self.label}: "
            + f" ({self.minVolume}, {self.maxVolume})"
            + f" -> ({self.minLimit},{self.maxLimit}). "
            + f" Periodicidade {self.frequency}"
        )
