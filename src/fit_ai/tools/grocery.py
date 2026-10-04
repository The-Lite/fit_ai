from __future__ import annotations

from decimal import Decimal

from pydantic import Field

from fit_ai.domain.baskets import BasketRequest
from fit_ai.domain.common import StrictModel
from fit_ai.domain.planning import FoodPlanRequest
from fit_ai.domain.price_matching import PriceMatchRequest
from fit_ai.domain.products import ProductSearchRequest
from fit_ai.repositories.database import create_database_engine
from fit_ai.repositories.product_repository import ProductRepository
from fit_ai.repositories.store_repository import StoreRepository
from fit_ai.repositories.user_repository import UserRepository
from fit_ai.services.basket_options import BasketOptionsService
from fit_ai.services.distances import DistanceService
from fit_ai.services.price_matching import PriceMatchService
from fit_ai.services.product_search import ProductSearchService
from fit_ai.services.user_context import UserContextService
from fit_ai.services.weekly_food_planning import WeeklyFoodPlanningService


class Coordinates(StrictModel):
    latitude: Decimal = Field(ge=-90, le=90)
    longitude: Decimal = Field(ge=-180, le=180)


class StoreDistanceRequest(StrictModel):
    user_location: Coordinates
    stores: tuple[str, ...] | None = None
    max_distance_km: Decimal | None = Field(default=None, gt=0)


def get_user_context(
    user_id: int, *, service: UserContextService | None = None
) -> dict[str, object]:
    active_service = service or UserContextService(
        UserRepository(create_database_engine())
    )
    context = active_service.get(user_id)
    return {
        "user": context.user.model_dump(mode="json"),
        "location": {
            "latitude": str(context.location.latitude),
            "longitude": str(context.location.longitude),
        },
        "shopping_preferences": {
            key: value
            for key, value in context.shopping_preferences.model_dump(
                mode="json"
            ).items()
            if key != "user_id"
        },
        "warnings": list(context.warnings),
    }


def get_store_distances(
    request: StoreDistanceRequest,
    *,
    service: DistanceService | None = None,
) -> dict[str, object]:
    active_service = service or DistanceService(
        StoreRepository(create_database_engine())
    )
    result = active_service.calculate(
        request.user_location.latitude,
        request.user_location.longitude,
        request.stores,
        request.max_distance_km,
    )
    payload = result.model_dump(mode="json")
    payload["origin"] = {
        "latitude": payload.pop("origin_latitude"),
        "longitude": payload.pop("origin_longitude"),
    }
    return payload


def search_current_products(
    request: ProductSearchRequest,
    *,
    service: ProductSearchService | None = None,
) -> dict[str, object]:
    active_service = service or ProductSearchService(
        ProductRepository(create_database_engine())
    )
    return active_service.search(request).model_dump(mode="json")


def plan_weekly_food_basket(
    request: FoodPlanRequest,
    *,
    service: WeeklyFoodPlanningService | None = None,
) -> dict[str, object]:
    return (
        (service or WeeklyFoodPlanningService()).plan(request).model_dump(mode="json")
    )


def check_price_match(
    request: PriceMatchRequest,
    *,
    service: PriceMatchService | None = None,
) -> dict[str, object]:
    active_service = service or PriceMatchService(
        ProductRepository(create_database_engine())
    )
    return active_service.check(request).model_dump(mode="json")


def build_basket_options(
    request: BasketRequest,
    *,
    service: BasketOptionsService | None = None,
) -> dict[str, object]:
    active_service = service or BasketOptionsService(
        ProductRepository(create_database_engine())
    )
    return active_service.build(request).model_dump(mode="json")
