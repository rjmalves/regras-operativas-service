from pydantic import BaseModel
from typing import List

from app.models.reservoirgrouprule import ReservoirGroupRule


class ReservoirRulesResponse(BaseModel):
    """
    Class for defining a reservoir rule application response, containing
    the rules that were applied.
    """

    result: List[ReservoirGroupRule]
