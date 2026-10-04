from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from typing import Any, Literal

from pydantic import Field, model_validator

from fit_ai.domain.common import Amount, ParsedPackage, StrictModel


class Product(StrictModel):
    product_id: str
    name: str
    brand: str | None = None
    size: str | None = None
    unit_price: dict[str, Any] | None = None
    image: str | None = None
    category_id: int | None = None
    price: Decimal | None = Field(default=None, ge=0)
    store: str | None = None
    discounted: bool | None = None
    prices: dict[str, Any] | list[Any] | str | None = None
    link: str | None = None
    url: str | None = None
    category_name: str | None = None
    updated: datetime | None = None
    loaded_at: datetime
    parsed_package: ParsedPackage | None = None


class FoodQuery(StrictModel):
    food_id: str = Field(min_length=1)
    name: str = Field(min_length=1, max_length=200)


class ProductSearchRequest(StrictModel):
    food_queries: tuple[FoodQuery, ...] = Field(max_length=30)
    stores: tuple[str, ...] | None = None
    limit_per_food: int = Field(default=20, gt=0, le=100)


class RankedProduct(Product):
    match_score: float = Field(ge=0, le=1)
    match_reason: str


class ProductMatch(StrictModel):
    food_id: str
    query: str
    matches: tuple[RankedProduct, ...]
    status: Literal["matched", "unmatched"]


class ProductSearchResult(StrictModel):
    current_snapshot_date: date
    product_matches: tuple[ProductMatch, ...]
    unmatched_foods: tuple[str, ...]
    warnings: tuple[str, ...] = ()


class QuantityRequest(StrictModel):
    food_id: str
    required_amount: Amount | None = None
    requested_packages: int | None = Field(default=None, gt=0)
    product: Product
    current_snapshot_date: date

    @model_validator(mode="after")
    def one_quantity_mode(self) -> QuantityRequest:
        if self.required_amount is not None and self.requested_packages is not None:
            raise ValueError("amount_and_package_count_are_mutually_exclusive")
        return self


class PurchaseCandidate(StrictModel):
    food_id: str
    product_id: str
    required_amount: Amount | None = None
    parsed_package: ParsedPackage | None = None
    packages_required: int = Field(gt=0)
    purchased_amount: Amount | None = None
    surplus_amount: Decimal | None = Field(default=None, ge=0)
    quantity_policy: Literal[
        "explicit_amount", "explicit_packages", "default_one_package"
    ] = "explicit_amount"
    line_total: Decimal = Field(ge=0)


class RejectedCandidate(StrictModel):
    food_id: str
    product_id: str
    reasons: tuple[str, ...]


class QuantityResult(StrictModel):
    purchase_candidate: PurchaseCandidate | None = None
    rejected_candidate: RejectedCandidate | None = None
