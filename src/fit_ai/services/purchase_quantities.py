from __future__ import annotations

from decimal import ROUND_CEILING, Decimal

from fit_ai.domain.common import Amount
from fit_ai.domain.products import (
    PurchaseCandidate,
    QuantityRequest,
    QuantityResult,
    RejectedCandidate,
)
from fit_ai.services.package_parsing import parse_package_size


class PurchaseQuantityService:
    """Calculate package counts from requested amount and actual package size."""

    def calculate(self, request: QuantityRequest) -> QuantityResult:
        reasons: list[str] = []
        product = request.product
        package = parse_package_size(product.size)
        if (
            product.updated is None
            or product.updated.date() != request.current_snapshot_date
        ):
            reasons.append("stale_product")
        if product.price is None:
            reasons.append("missing_price")
        if package is None and request.required_amount is not None:
            reasons.append("missing_package_size")
        elif (
            package
            and request.required_amount
            and package.unit != request.required_amount.unit
        ):
            reasons.append("incompatible_units")
        if reasons:
            return QuantityResult(
                rejected_candidate=RejectedCandidate(
                    food_id=request.food_id,
                    product_id=product.product_id,
                    reasons=tuple(reasons),
                )
            )
        assert product.price is not None
        if request.required_amount is not None:
            assert package is not None
            packages = int(
                (request.required_amount.value / package.amount).to_integral_value(
                    rounding=ROUND_CEILING
                )
            )
            policy = "explicit_amount"
        else:
            packages = request.requested_packages or 1
            policy = (
                "explicit_packages"
                if request.requested_packages
                else "default_one_package"
            )
        purchased = package.amount * packages if package else None
        return QuantityResult(
            purchase_candidate=PurchaseCandidate(
                food_id=request.food_id,
                product_id=product.product_id,
                required_amount=request.required_amount,
                parsed_package=package,
                packages_required=packages,
                purchased_amount=Amount(value=purchased, unit=package.unit)
                if package
                else None,
                surplus_amount=purchased - request.required_amount.value
                if request.required_amount
                else None,
                line_total=product.price * Decimal(packages),
                quantity_policy=policy,
            )
        )
