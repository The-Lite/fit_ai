from __future__ import annotations

from decimal import Decimal
from enum import Enum

from pydantic import BaseModel, ConfigDict, Field


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


class PackageUnit(str, Enum):
    GRAM = "g"
    MILLILITER = "ml"
    UNIT = "unit"


class Amount(StrictModel):
    value: Decimal = Field(gt=0)
    unit: PackageUnit


class ParsedPackage(StrictModel):
    amount: Decimal = Field(gt=0)
    unit: PackageUnit
    source_field: str


class WarningResult(StrictModel):
    warnings: tuple[str, ...] = ()
