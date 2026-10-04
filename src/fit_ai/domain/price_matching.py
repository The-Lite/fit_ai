from datetime import date
from decimal import Decimal

from pydantic import Field

from fit_ai.domain.common import StrictModel


class PriceMatchPair(StrictModel):
    food_id: str
    maxi_product_id: str
    competitor_product_id: str
    packages_requested: int = Field(default=1, gt=0)


class PriceMatchRequest(StrictModel):
    pairs: tuple[PriceMatchPair, ...] = Field(max_length=1000)


class PriceMatchEvaluation(PriceMatchPair):
    eligible: bool
    reasons: tuple[str, ...] = ()
    competitor_store: str | None = None
    matched_unit_price: Decimal | None = None
    quantity_matched: int = Field(default=0, ge=0, le=4)
    quantity_not_matched: int = Field(ge=0)
    estimated_savings: Decimal = Field(default=Decimal(0), ge=0)
    effective_total: Decimal | None = None
    source_url: str | None = None


class PriceMatchResult(StrictModel):
    current_snapshot_date: date
    price_match_results: tuple[PriceMatchEvaluation, ...]
    warnings: tuple[str, ...] = ()
