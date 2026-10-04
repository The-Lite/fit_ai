from __future__ import annotations

from datetime import date
from decimal import Decimal

from pydantic import Field, field_validator

from fit_ai.domain.common import StrictModel
from fit_ai.domain.planning import FoodPlan
from fit_ai.domain.price_matching import PriceMatchRequest, PriceMatchResult
from fit_ai.domain.products import ProductSearchResult, PurchaseCandidate
from fit_ai.domain.stores import StoreDistanceResult
from fit_ai.domain.users import ShoppingPreferences


class BasketRequest(StrictModel):
    food_plan: FoodPlan
    search_result: ProductSearchResult
    store_distances: StoreDistanceResult
    shopping_preferences: ShoppingPreferences
    price_matches: PriceMatchRequest = PriceMatchRequest(pairs=())

    @field_validator("price_matches", mode="before")
    @classmethod
    def accept_price_match_tool_payload(cls, value: object) -> object:
        if isinstance(value, PriceMatchResult):
            value = value.model_dump()
        if isinstance(value, dict) and "price_match_results" in value:
            fields = (
                "food_id",
                "maxi_product_id",
                "competitor_product_id",
                "packages_requested",
            )
            return {
                "pairs": [
                    {key: row[key] for key in fields}
                    for row in value["price_match_results"]
                ]
            }
        return value

    @field_validator("store_distances", mode="before")
    @classmethod
    def accept_distance_tool_payload(cls, value: object) -> object:
        if isinstance(value, dict) and "origin" in value:
            value = dict(value)
            origin = value.pop("origin")
            value.update(
                origin_latitude=origin["latitude"], origin_longitude=origin["longitude"]
            )
        return value


class BasketItem(StrictModel):
    food_id: str
    product_id: str
    product_name: str
    store: str
    quantity: PurchaseCandidate
    match_score: float
    line_total: Decimal = Field(ge=0)
    price_match_savings: Decimal = Field(default=Decimal(0), ge=0)
    quantity_matched: int = Field(default=0, ge=0, le=4)
    competitor_product_id: str | None = None


class UnfulfilledFood(StrictModel):
    food_id: str
    food_name: str
    reasons: tuple[str, ...]


class BasketOption(StrictModel):
    option_id: str
    strategy_type: str
    selected_items: tuple[BasketItem, ...]
    stores: tuple[str, ...]
    store_location_ids: tuple[int, ...]
    total: Decimal
    budget: Decimal | None
    within_budget: bool
    estimated_savings: Decimal
    distance_km: Decimal
    required_foods_fulfilled: int
    optional_foods_fulfilled: int
    unfulfilled_foods: tuple[UnfulfilledFood, ...]
    excluded_optional_foods: tuple[UnfulfilledFood, ...]
    complete: bool
    extra_store_savings: Decimal | None = None
    warnings: tuple[str, ...] = ()


class BasketResult(StrictModel):
    current_snapshot_date: date
    options: tuple[BasketOption, ...]
    rejected_reasons: tuple[str, ...] = ()
    warnings: tuple[str, ...] = ()
    algorithm: str = "exact_dynamic_programming_over_retrieved_candidates"
