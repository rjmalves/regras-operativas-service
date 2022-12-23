from pydantic import BaseModel
from typing import Optional


class ReservoirRule(BaseModel):
    """
    Class for defining a reservoir operation rule
    based on other states.
    """

    reservoirCode: int
    uheCode: int
    constraintType: str
    month: int
    minVolume: float
    maxVolume: float
    minLimit: float
    maxLimit: float
    frequency: str
    label: Optional[str]

    def __str__(self) -> str:
        return (
            f"Regra: reservatório {self.reservoirCode}"
            + f" -> usina {self.uheCode} | {self.constraintType}"
            + f" mês {self.month}. Faixa {self.label}: "
            + f" ({self.minVolume}, {self.maxVolume})"
            + f" -> ({self.minLimit},{self.maxLimit}). "
            + f" Periodicidade {self.frequency}"
        )
