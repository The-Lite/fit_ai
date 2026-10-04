from decimal import Decimal

import pytest

from fit_ai.domain.errors import NotFoundError
from fit_ai.domain.users import ShoppingPreferences, User, UserLocation
from fit_ai.services.user_context import UserContextService


class FakeUserRepository:
    def __init__(self, missing: str | None = None) -> None:
        self.missing = missing

    def get_user(self, user_id):
        if self.missing == "user":
            return None
        return User(
            user_id=user_id,
            username="Alice",
            age=30,
            weight_kg=Decimal(80),
            height_cm=Decimal(185),
            goal="muscle_gain",
            vegetarian=0,
            budget=Decimal(100),
        )

    def get_location(self, user_id):
        if self.missing == "location":
            return None
        return UserLocation(
            user_id=user_id, latitude=Decimal(45), longitude=Decimal(-73)
        )

    def get_preferences(self, user_id):
        if self.missing == "preferences":
            return None
        return ShoppingPreferences(
            user_id=user_id,
            shopping_priority="balanced",
            max_stores=2,
            max_distance_km=Decimal(10),
            minimum_savings_for_extra_store=Decimal(5),
        )


def test_builds_user_context() -> None:
    result = UserContextService(FakeUserRepository()).get(1)
    assert result.user.user_id == 1
    assert result.user.vegetarian is False


@pytest.mark.parametrize("missing", ["user", "location", "preferences"])
def test_missing_context_component_is_explicit(missing: str) -> None:
    with pytest.raises(NotFoundError):
        UserContextService(FakeUserRepository(missing)).get(1)
