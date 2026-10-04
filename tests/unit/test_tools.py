from decimal import Decimal

from fit_ai.domain.stores import StoreDistanceResult
from fit_ai.domain.users import (
    ShoppingPreferences,
    User,
    UserContext,
    UserLocation,
)
from fit_ai.tools.grocery import (
    Coordinates,
    StoreDistanceRequest,
    get_store_distances,
    get_user_context,
)


class FakeUserContextService:
    def get(self, user_id):
        return UserContext(
            user=User(
                user_id=user_id,
                username="Alice",
                age=30,
                weight_kg=80,
                height_cm=185,
                goal="maintenance",
                vegetarian=0,
                budget=100,
            ),
            location=UserLocation(user_id=user_id, latitude=45, longitude=-73),
            shopping_preferences=ShoppingPreferences(
                user_id=user_id,
                shopping_priority="balanced",
                max_stores=2,
                max_distance_km=10,
                minimum_savings_for_extra_store=5,
            ),
        )


class FakeDistanceService:
    def calculate(self, latitude, longitude, stores, max_distance_km):
        return StoreDistanceResult(
            origin_latitude=latitude,
            origin_longitude=longitude,
            stores=(),
            warnings=("no_store_locations_found",),
        )


def test_get_user_context_contract_shape() -> None:
    result = get_user_context(1, service=FakeUserContextService())
    assert result["location"] == {"latitude": "45", "longitude": "-73"}
    assert "user_id" not in result["shopping_preferences"]


def test_get_store_distances_contract_shape() -> None:
    request = StoreDistanceRequest(
        user_location=Coordinates(latitude=Decimal(45), longitude=Decimal(-73))
    )
    result = get_store_distances(request, service=FakeDistanceService())
    assert result["origin"] == {"latitude": "45", "longitude": "-73"}
    assert "origin_latitude" not in result
