from __future__ import annotations

import os

import pytest

from fit_ai.repositories.database import create_database_engine
from fit_ai.repositories.product_repository import ProductRepository
from fit_ai.repositories.store_repository import StoreRepository
from fit_ai.repositories.user_repository import UserRepository

DATABASE_URL = os.getenv("FIT_AI_INTEGRATION_DATABASE_URL")
pytestmark = pytest.mark.skipif(
    not DATABASE_URL,
    reason="FIT_AI_INTEGRATION_DATABASE_URL is not configured",
)


@pytest.fixture(scope="module")
def engine():
    active_engine = create_database_engine(DATABASE_URL)
    yield active_engine
    active_engine.dispose()


def test_user_repository_reads_verified_schema(engine) -> None:
    repository = UserRepository(engine)
    user = repository.get_user(1)
    assert user is not None
    assert repository.get_location(1) is not None
    assert repository.get_preferences(1) is not None


def test_store_repository_filters_known_brand(engine) -> None:
    stores = StoreRepository(engine).list_locations(("maxi",))
    assert stores
    assert {store.store for store in stores} == {"maxi"}


def test_product_repository_returns_only_latest_snapshot(engine) -> None:
    repository = ProductRepository(engine)
    snapshot = repository.get_current_snapshot_date()
    assert snapshot is not None
    products = repository.search_current("rice", limit=10)
    assert all(product.updated is not None for product in products)
    assert all(
        product.updated.date() == snapshot for product in products if product.updated
    )
