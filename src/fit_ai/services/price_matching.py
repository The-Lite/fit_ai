from __future__ import annotations

from datetime import date
from decimal import Decimal

from fit_ai.domain.errors import NotFoundError
from fit_ai.domain.food_matching import normalize
from fit_ai.domain.price_matching import (
    PriceMatchEvaluation,
    PriceMatchPair,
    PriceMatchRequest,
    PriceMatchResult,
)
from fit_ai.domain.products import Product
from fit_ai.domain.store_identity import PRICE_MATCH_COMPETITORS, store_identity
from fit_ai.repositories.product_repository import ProductRepository
from fit_ai.services.package_parsing import parse_package_size


def identity_key(product: Product) -> tuple[str, str, str]:
    package = parse_package_size(product.size)
    size = f"{package.amount.normalize()}:{package.unit.value}" if package else ""
    return normalize(product.name), normalize(product.brand or ""), size


class PriceMatchService:
    def __init__(self, repository: ProductRepository) -> None:
        self._repository = repository

    def check(self, request: PriceMatchRequest) -> PriceMatchResult:
        ids = tuple(
            sorted(
                {
                    p
                    for pair in request.pairs
                    for p in (pair.maxi_product_id, pair.competitor_product_id)
                }
            )
        )
        snapshot, products = self._repository.current_by_ids(ids)
        if snapshot is None:
            raise NotFoundError("current_product_snapshot_not_found")
        by_id = {p.product_id: p for p in products}
        return PriceMatchResult(
            current_snapshot_date=snapshot,
            price_match_results=tuple(
                self.evaluate(pair, by_id, snapshot) for pair in request.pairs
            ),
            warnings=(
                "pair_estimates_are_not_additive_four_package_cap_applies_per_identical_item",
            ),
        )

    @staticmethod
    def evaluate(
        pair: PriceMatchPair, products: dict[str, Product], snapshot: date
    ) -> PriceMatchEvaluation:
        maxi = products.get(pair.maxi_product_id)
        competitor = products.get(pair.competitor_product_id)
        reasons = []
        for label, product in (("maxi", maxi), ("competitor", competitor)):
            if product is None:
                reasons.append(f"{label}_product_not_current_or_not_found")
                continue
            if product.updated is None or product.updated.date() != snapshot:
                reasons.append(f"stale_{label}_product")
            if not normalize(product.brand or ""):
                reasons.append(f"missing_{label}_brand")
            if not product.size:
                reasons.append(f"missing_{label}_size")
            elif parse_package_size(product.size) is None:
                reasons.append(f"unparseable_{label}_size")
            if product.price is None:
                reasons.append(f"missing_{label}_price")
        if maxi and store_identity(maxi.store) != "maxi":
            reasons.append("maxi_does_not_carry_referenced_product")
        if (
            competitor
            and store_identity(competitor.store) not in PRICE_MATCH_COMPETITORS
        ):
            reasons.append("ineligible_competitor")
        if maxi and competitor:
            left, right = identity_key(maxi), identity_key(competitor)
            if left[0] != right[0]:
                reasons.append("identical_product_not_proven")
            if left[1] != right[1]:
                reasons.append("brand_mismatch")
            if left[2] != right[2]:
                reasons.append("size_mismatch")
            if (
                maxi.price is not None
                and competitor.price is not None
                and competitor.price >= maxi.price
            ):
                reasons.append("no_price_advantage")
        eligible = not reasons
        count = min(pair.packages_requested, 4) if eligible else 0
        savings = (maxi.price - competitor.price) * count if eligible else Decimal(0)
        total = (
            maxi.price * pair.packages_requested - savings
            if maxi and maxi.price is not None
            else None
        )
        return PriceMatchEvaluation(
            **pair.model_dump(),
            eligible=eligible,
            reasons=tuple(reasons),
            competitor_store=competitor.store if competitor else None,
            matched_unit_price=competitor.price if eligible else None,
            quantity_matched=count,
            quantity_not_matched=pair.packages_requested - count,
            estimated_savings=savings,
            effective_total=total,
            source_url=(competitor.link or competitor.url) if competitor else None,
        )
