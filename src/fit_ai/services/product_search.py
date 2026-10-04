from __future__ import annotations

from fit_ai.config.food_catalog import CANDIDATE_LIMIT, MIN_RELEVANCE
from fit_ai.domain.errors import NotFoundError, ValidationFailure
from fit_ai.domain.food_matching import query_aliases, rank_product
from fit_ai.domain.products import (
    ProductMatch,
    ProductSearchRequest,
    ProductSearchResult,
    RankedProduct,
)
from fit_ai.repositories.product_repository import ProductRepository
from fit_ai.services.package_parsing import parse_package_size


class ProductSearchService:
    def __init__(self, repository: ProductRepository) -> None:
        self._repository = repository

    def search(self, request: ProductSearchRequest) -> ProductSearchResult:
        if len({food.food_id for food in request.food_queries}) != len(
            request.food_queries
        ):
            raise ValidationFailure("duplicate_food_id")
        snapshot, batches = self._repository.search_batch(
            tuple(food.name for food in request.food_queries),
            request.stores,
            CANDIDATE_LIMIT,
        )
        if snapshot is None:
            raise NotFoundError("current_product_snapshot_not_found")
        groups: list[ProductMatch] = []
        unmatched: list[str] = []
        warnings: list[str] = []
        for food, products in zip(request.food_queries, batches):
            ranked = []
            if len(products) == CANDIDATE_LIMIT:
                warnings.append(f"candidate_limit_reached:{food.food_id}")
            if query_aliases(food.name)[0] is None:
                warnings.append(f"unmapped_query_no_bilingual_expansion:{food.food_id}")
            for product in products:
                if product.updated is None or product.updated.date() != snapshot:
                    warnings.append(f"stale_product_rejected:{product.product_id}")
                    continue
                score, reason = rank_product(food.name, product)
                if score >= MIN_RELEVANCE:
                    ranked.append(
                        RankedProduct(
                            **product.model_dump(exclude={"parsed_package"}),
                            parsed_package=parse_package_size(product.size),
                            match_score=score,
                            match_reason=reason,
                        )
                    )
            parsed = tuple(
                sorted(ranked, key=lambda p: (-p.match_score, p.product_id))[
                    : request.limit_per_food
                ]
            )
            if not parsed:
                unmatched.append(food.food_id)
            if any(product.parsed_package is None for product in parsed):
                warnings.append(f"unparseable_package_size:{food.food_id}")
            groups.append(
                ProductMatch(
                    food_id=food.food_id,
                    query=food.name,
                    matches=parsed,
                    status="matched" if parsed else "unmatched",
                )
            )
        return ProductSearchResult(
            current_snapshot_date=snapshot,
            product_matches=tuple(groups),
            unmatched_foods=tuple(unmatched),
            warnings=tuple(sorted(set(warnings))),
        )
