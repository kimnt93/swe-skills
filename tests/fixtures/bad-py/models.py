"""Breaks the py-code import rule twice; ruff must report both."""

import pandas
from pydantic import BaseModel


class Order(BaseModel):
    id: str


FRAME = pandas.DataFrame()
