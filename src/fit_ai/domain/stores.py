from __future__ import annotations

from decimal import Decimal

from pydantic import Field

from fit_ai.domain.common import StrictModel


class StoreLocation(StrictModel):
    store_location_id: int = Field(gt=0)
    store: str
    store_name: str
    latitude: Decimal = Field(ge=-90, le=90)
    longitude: Decimal = Field(ge=-180, le=180)


class StoreDistance(StrictModel):
    store_location_id: int
    store: str
    store_name: str
    latitude: Decimal
    longitude: Decimal
    distance_km: Decimal = Field(ge=0)
    within_max_distance: bool


class StoreDistanceResult(StrictModel):
    origin_latitude: Decimal
    origin_longitude: Decimal
    stores: tuple[StoreDistance, ...]
    distance_method: str = "lat_lon_haversine"
    warnings: tuple[str, ...] = ()
