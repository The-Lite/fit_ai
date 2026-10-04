from fit_ai.domain.errors import NotFoundError
from fit_ai.domain.users import UserContext
from fit_ai.repositories.user_repository import UserRepository


class UserContextService:
    def __init__(self, repository: UserRepository) -> None:
        self._repository = repository

    def get(self, user_id: int) -> UserContext:
        user = self._repository.get_user(user_id)
        if user is None:
            raise NotFoundError("user_not_found")
        location = self._repository.get_location(user_id)
        if location is None:
            raise NotFoundError("user_location_not_found")
        preferences = self._repository.get_preferences(user_id)
        if preferences is None:
            raise NotFoundError("shopping_preferences_not_found")
        return UserContext(
            user=user, location=location, shopping_preferences=preferences
        )
