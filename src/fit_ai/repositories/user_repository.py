from __future__ import annotations

from sqlalchemy import Engine, text
from sqlalchemy.exc import SQLAlchemyError

from fit_ai.domain.errors import RepositoryError
from fit_ai.domain.users import ShoppingPreferences, User, UserLocation


class UserRepository:
    def __init__(self, engine: Engine) -> None:
        self._engine = engine

    def get_user(self, user_id: int) -> User | None:
        row = self._one(
            """SELECT user_id, username, age, weight_kg, height_cm, goal,
                      vegetarian, budget
               FROM public.users WHERE user_id = :user_id""",
            user_id,
        )
        return User.model_validate(row) if row else None

    def get_location(self, user_id: int) -> UserLocation | None:
        row = self._one(
            """SELECT user_id, latitude, longitude
               FROM public.user_locations WHERE user_id = :user_id""",
            user_id,
        )
        return UserLocation.model_validate(row) if row else None

    def get_preferences(self, user_id: int) -> ShoppingPreferences | None:
        row = self._one(
            """SELECT user_id, shopping_priority, max_stores, max_distance_km,
                      minimum_savings_for_extra_store
               FROM public.user_shopping_preferences WHERE user_id = :user_id""",
            user_id,
        )
        return ShoppingPreferences.model_validate(row) if row else None

    def _one(self, statement: str, user_id: int) -> dict[str, object] | None:
        try:
            with self._engine.connect() as connection:
                row = (
                    connection.execute(text(statement), {"user_id": user_id})
                    .mappings()
                    .one_or_none()
                )
                return dict(row) if row else None
        except SQLAlchemyError as exc:
            raise RepositoryError("User data could not be read") from exc
