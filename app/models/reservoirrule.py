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
    minLimit: Optional[float]
    maxLimit: Optional[float]
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

    def __key(self):
        return (
            self.reservoirCode,
            self.uheCode,
            self.constraintType,
            self.month,
            self.label,
            self.minVolume,
            self.maxVolume,
            self.minLimit,
            self.maxLimit,
        )

    def __hash__(self):
        return hash(self.__key())

    def __eq__(self, other):
        if isinstance(other, ReservoirRule):
            return self.__key() == other.__key()
        return NotImplemented
