from __future__ import annotations

from decimal import Decimal
from enum import Enum

from pydantic import Field, field_validator

from fit_ai.domain.common import StrictModel


class ShoppingPriority(str, Enum):
    BALANCED = "balanced"
    CONVENIENCE = "convenience"
    SAVINGS = "savings"


class User(StrictModel):
    user_id: int = Field(gt=0)
    username: str
    age: int = Field(gt=0)
    weight_kg: Decimal = Field(gt=0)
    height_cm: Decimal = Field(gt=0)
    goal: str
    vegetarian: bool
    budget: Decimal = Field(ge=0)

    @field_validator("vegetarian", mode="before")
    @classmethod
    def normalize_vegetarian(cls, value: object) -> object:
        if value in (0, 1):
            return bool(value)
        return value


class UserLocation(StrictModel):
    user_id: int = Field(gt=0)
    latitude: Decimal = Field(ge=-90, le=90)
    longitude: Decimal = Field(ge=-180, le=180)


class ShoppingPreferences(StrictModel):
    user_id: int = Field(gt=0)
    shopping_priority: ShoppingPriority
    max_stores: int = Field(gt=0)
    max_distance_km: Decimal = Field(gt=0)
    minimum_savings_for_extra_store: Decimal = Field(ge=0)


class UserContext(StrictModel):
    user: User
    location: UserLocation
    shopping_preferences: ShoppingPreferences
    warnings: tuple[str, ...] = ()
