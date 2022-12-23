from pydantic import BaseModel
from typing import List
from app.models.case import Case
from app.models.reservoirrule import ReservoirRule


class ReservoirRulesRequest(BaseModel):
    """
    Class for defining a rule application request that relates to a case.
    """

    sources: List[Case]
    destination: Case
    rules: List[ReservoirRule]
