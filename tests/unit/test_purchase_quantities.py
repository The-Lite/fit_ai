from datetime import date, datetime, timezone
from decimal import Decimal

from fit_ai.domain.common import Amount, PackageUnit
from fit_ai.domain.products import Product, QuantityRequest
from fit_ai.services.package_parsing import parse_package_size
from fit_ai.services.purchase_quantities import PurchaseQuantityService


def product(*, size: str = "900g", price: Decimal | None = Decimal("8.50")) -> Product:
    return Product(
        product_id="p1",
        name="Chicken",
        size=size,
        price=price,
        store="maxi",
        updated=datetime(2026, 9, 13, tzinfo=timezone.utc),
        loaded_at=datetime(2026, 9, 13, tzinfo=timezone.utc),
        parsed_package=parse_package_size(size),
    )


def test_calculates_packages_surplus_and_total_deterministically() -> None:
    result = PurchaseQuantityService().calculate(
        QuantityRequest(
            food_id="chicken",
            required_amount=Amount(value=Decimal(2000), unit=PackageUnit.GRAM),
            product=product(),
            current_snapshot_date=date(2026, 9, 13),
        )
    )
    candidate = result.purchase_candidate
    assert candidate is not None
    assert candidate.packages_required == 3
    assert candidate.purchased_amount.value == Decimal(2700)
    assert candidate.surplus_amount == Decimal(700)
    assert candidate.line_total == Decimal("25.50")


def test_rejects_incompatible_units() -> None:
    result = PurchaseQuantityService().calculate(
        QuantityRequest(
            food_id="milk",
            required_amount=Amount(value=Decimal(1000), unit=PackageUnit.MILLILITER),
            product=product(),
            current_snapshot_date=date(2026, 9, 13),
        )
    )
    assert result.rejected_candidate is not None
    assert "incompatible_units" in result.rejected_candidate.reasons


def test_rejects_stale_product_and_missing_price() -> None:
    result = PurchaseQuantityService().calculate(
        QuantityRequest(
            food_id="chicken",
            required_amount=Amount(value=Decimal(100), unit=PackageUnit.GRAM),
            product=product(price=None),
            current_snapshot_date=date(2026, 9, 14),
        )
    )
    assert result.rejected_candidate is not None
    assert result.rejected_candidate.reasons == ("stale_product", "missing_price")
