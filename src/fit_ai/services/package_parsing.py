from __future__ import annotations

import re
from decimal import Decimal, InvalidOperation

from fit_ai.domain.common import PackageUnit, ParsedPackage

_SIZE_PATTERN = re.compile(
    r"^\s*(?P<amount>\d+(?:[.,]\d+)?)\s*(?P<unit>kg|g|ml|l|units?|un|count|ct|eggs?)\s*$",
    re.IGNORECASE,
)


def parse_package_size(size: str | None) -> ParsedPackage | None:
    if not size:
        return None
    match = _SIZE_PATTERN.fullmatch(size)
    if not match:
        return None
    try:
        amount = Decimal(match.group("amount").replace(",", "."))
    except InvalidOperation:
        return None
    raw_unit = match.group("unit").lower()
    if raw_unit == "kg":
        amount *= Decimal(1000)
        unit = PackageUnit.GRAM
    elif raw_unit == "l":
        amount *= Decimal(1000)
        unit = PackageUnit.MILLILITER
    elif raw_unit == "g":
        unit = PackageUnit.GRAM
    elif raw_unit == "ml":
        unit = PackageUnit.MILLILITER
    else:
        unit = PackageUnit.UNIT
    if amount <= 0:
        return None
    return ParsedPackage(amount=amount, unit=unit, source_field="size")
