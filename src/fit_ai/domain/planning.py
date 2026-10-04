from __future__ import annotations

from decimal import Decimal
from typing import Literal

from pydantic import Field, field_validator, model_validator

from fit_ai.domain.common import Amount, StrictModel
from fit_ai.domain.users import UserContext


class FoodInput(StrictModel):
    food_id: str = Field(min_length=1)
    food_name: str = Field(min_length=1)
    requested_quantity: Decimal | None = Field(default=None, gt=0)
    requested_unit: (
        Literal["g", "kg", "ml", "l", "unit", "egg", "eggs", "package", "bag", "bags"]
        | None
    ) = None

    @model_validator(mode="after")
    def quantity_pair(self) -> FoodInput:
        if (self.requested_quantity is None) != (self.requested_unit is None):
            raise ValueError("quantity_and_unit_required_together")
        if (
            self.requested_unit in {"package", "bag", "bags", "unit", "egg", "eggs"}
            and self.requested_quantity != self.requested_quantity.to_integral_value()
        ):
            raise ValueError("count_must_be_integer")
        return self


class FoodRequirement(FoodInput):
    source: Literal["user", "default_planner"]
    priority: Literal["required", "optional"]
    concept_id: str | None = None
    required_amount: Amount | None = None
    requested_packages: int | None = Field(default=None, gt=0)
    restriction_reasons: tuple[str, ...] = ()

    @model_validator(mode="after")
    def normalized_contract(self) -> FoodRequirement:
        if (self.source == "user") != (self.priority == "required"):
            raise ValueError("invalid_food_source_priority")
        quantity, unit = self.requested_quantity, self.requested_unit
        if quantity is None:
            if self.required_amount is not None or self.requested_packages is not None:
                raise ValueError("unexpected_normalized_quantity")
        elif unit in {"package", "bag", "bags"}:
            if (
                self.requested_packages != int(quantity)
                or self.required_amount is not None
            ):
                raise ValueError("inconsistent_package_quantity")
        else:
            normalized_unit = {"kg": "g", "l": "ml", "egg": "unit", "eggs": "unit"}.get(
                unit, unit
            )
            amount = quantity * (1000 if unit in {"kg", "l"} else 1)
            if (
                self.required_amount != Amount(value=amount, unit=normalized_unit)
                or self.requested_packages is not None
            ):
                raise ValueError("inconsistent_amount_quantity")
        return self


class PlanningContext(StrictModel):
    """Declared runtime values; not claimed to be PostgreSQL profile columns."""

    source: Literal["runtime"] = "runtime"
    eats_fish: bool | None = None
    preferred_foods: tuple[str, ...] = ()
    excluded_foods: tuple[str, ...] = ()
    preferred_categories: tuple[str, ...] = ()
    excluded_categories: tuple[str, ...] = ()
    allergies: tuple[str, ...] = ()
    dietary_restrictions: tuple[str, ...] = ()


class FoodPlanRequest(StrictModel):
    user_context: UserContext
    foods: tuple[FoodInput, ...] = Field(default=(), max_length=30)
    planning_context: PlanningContext = PlanningContext()
    budget: Decimal | None = Field(default=None, ge=0)

    @field_validator("user_context", mode="before")
    @classmethod
    def accept_user_tool_payload(cls, value: object) -> object:
        if isinstance(value, dict) and "user" in value:
            value = dict(value)
            for key in ("location", "shopping_preferences"):
                if key in value:
                    value[key] = {"user_id": value["user"]["user_id"], **value[key]}
        return value


class FoodPlan(StrictModel):
    foods: tuple[FoodRequirement, ...]
    budget: Decimal | None = Field(default=None, ge=0)
    mode: Literal["user", "automatic"]
    catalog_version: str
    planning_context: PlanningContext
    forbidden_tags: tuple[str, ...] = ()
    warnings: tuple[str, ...] = ()
