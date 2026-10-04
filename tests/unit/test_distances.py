from decimal import Decimal

from fit_ai.domain.stores import StoreLocation
from fit_ai.services.distances import DistanceService, haversine_km


class FakeStoreRepository:
    def list_locations(self, stores=None):
        locations = (
            StoreLocation(
                store_location_id=1,
                store="maxi",
                store_name="Maxi",
                latitude=Decimal("45.515"),
                longitude=Decimal("-73.561"),
            ),
        )
        return locations if not stores or "maxi" in stores else ()


def test_haversine_same_point_is_zero() -> None:
    assert haversine_km(Decimal(45), Decimal(-73), Decimal(45), Decimal(-73)) == 0


def test_distance_service_applies_maximum() -> None:
    result = DistanceService(FakeStoreRepository()).calculate(
        Decimal("45.500"), Decimal("-73.560"), max_distance_km=Decimal(1)
    )
    assert len(result.stores) == 1
    assert result.stores[0].distance_km > Decimal(1)
    assert result.stores[0].within_max_distance is False
