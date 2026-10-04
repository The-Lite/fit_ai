from __future__ import annotations

from decimal import ROUND_HALF_UP, Decimal
from math import asin, cos, radians, sin, sqrt

from fit_ai.domain.stores import StoreDistance, StoreDistanceResult
from fit_ai.repositories.store_repository import StoreRepository

EARTH_RADIUS_KM = 6371.0088


def haversine_km(lat1: Decimal, lon1: Decimal, lat2: Decimal, lon2: Decimal) -> Decimal:
    phi1, phi2 = radians(float(lat1)), radians(float(lat2))
    delta_phi = radians(float(lat2 - lat1))
    delta_lambda = radians(float(lon2 - lon1))
    a = sin(delta_phi / 2) ** 2 + cos(phi1) * cos(phi2) * sin(delta_lambda / 2) ** 2
    distance = EARTH_RADIUS_KM * 2 * asin(sqrt(a))
    return Decimal(str(distance)).quantize(Decimal("0.001"), rounding=ROUND_HALF_UP)


class DistanceService:
    def __init__(self, repository: StoreRepository) -> None:
        self._repository = repository

    def calculate(
        self,
        latitude: Decimal,
        longitude: Decimal,
        stores: tuple[str, ...] | None = None,
        max_distance_km: Decimal | None = None,
    ) -> StoreDistanceResult:
        locations = self._repository.list_locations(stores)
        results = []
        for location in locations:
            distance = haversine_km(
                latitude, longitude, location.latitude, location.longitude
            )
            results.append(
                StoreDistance(
                    **location.model_dump(),
                    distance_km=distance,
                    within_max_distance=max_distance_km is None
                    or distance <= max_distance_km,
                )
            )
        return StoreDistanceResult(
            origin_latitude=latitude,
            origin_longitude=longitude,
            stores=tuple(
                sorted(
                    results, key=lambda item: (item.distance_km, item.store_location_id)
                )
            ),
            warnings=("no_store_locations_found",) if not results else (),
        )
