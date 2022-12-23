from pydantic import BaseModel
from app.models.program import Program


class Case(BaseModel):
    """
    Class for defining a case that can be modified.
    """

    id: str
    program: Program
