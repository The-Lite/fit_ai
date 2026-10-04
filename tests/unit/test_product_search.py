from datetime import date, datetime, timezone
from decimal import Decimal

from fit_ai.domain.products import FoodQuery, Product, ProductSearchRequest
from fit_ai.services.product_search import ProductSearchService


class FakeProductRepository:
    def search_batch(self, queries, stores, limit):
        return date(2026, 9, 13), tuple(
            self.search_current(query, stores, limit) for query in queries
        )

    def search_current(self, query, stores, limit):
        if query == "missing":
            return ()
        return (
            Product(
                product_id="p1",
                name="Rice",
                size="1kg",
                price=Decimal("4.00"),
                store="maxi",
                updated=datetime(2026, 9, 13, tzinfo=timezone.utc),
                loaded_at=datetime(2026, 9, 13, tzinfo=timezone.utc),
            ),
        )


def test_search_groups_matches_and_parses_packages() -> None:
    result = ProductSearchService(FakeProductRepository()).search(
        ProductSearchRequest(
            food_queries=(
                FoodQuery(food_id="rice", name="rice"),
                FoodQuery(food_id="x", name="missing"),
            )
        )
    )
    assert result.current_snapshot_date == date(2026, 9, 13)
    assert result.product_matches[0].matches[0].parsed_package.amount == Decimal(1000)
    assert result.unmatched_foods == ("x",)
