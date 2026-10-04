from decimal import Decimal

import pytest

from fit_ai.domain.common import PackageUnit
from fit_ai.services.package_parsing import parse_package_size


@pytest.mark.parametrize(
    ("raw", "amount", "unit"),
    [
        ("680g", Decimal(680), PackageUnit.GRAM),
        ("1 kg", Decimal(1000), PackageUnit.GRAM),
        ("1.5L", Decimal("1500.0"), PackageUnit.MILLILITER),
        ("398ml", Decimal(398), PackageUnit.MILLILITER),
        ("30 eggs", Decimal(30), PackageUnit.UNIT),
        ("12 units", Decimal(12), PackageUnit.UNIT),
    ],
)
def test_parse_supported_package_sizes(
    raw: str, amount: Decimal, unit: PackageUnit
) -> None:
    parsed = parse_package_size(raw)
    assert parsed is not None
    assert parsed.amount == amount
    assert parsed.unit == unit


@pytest.mark.parametrize(
    "raw", [None, "", "2 x 500g", "16107ml extra", "unknown", "0g"]
)
def test_reject_unsupported_or_invalid_package_sizes(raw: str | None) -> None:
    assert parse_package_size(raw) is None
