from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from decimal import Decimal

from fit_ai.config.food_catalog import FOOD_CONCEPTS, MIN_RELEVANCE
from fit_ai.config.optimization import MAX_OPTIMIZER_STATES, MAX_OPTIMIZER_TRANSITIONS
from fit_ai.domain.baskets import (
    BasketItem,
    BasketOption,
    BasketRequest,
    BasketResult,
    UnfulfilledFood,
)
from fit_ai.domain.errors import NotFoundError, ValidationFailure
from fit_ai.domain.food_matching import contains, normalize, rank_product
from fit_ai.domain.price_matching import PriceMatchPair
from fit_ai.domain.products import QuantityRequest
from fit_ai.domain.store_identity import store_identity
from fit_ai.repositories.product_repository import ProductRepository
from fit_ai.services.price_matching import PriceMatchService, identity_key
from fit_ai.services.purchase_quantities import PurchaseQuantityService


@dataclass(frozen=True)
class Choice:
    item: BasketItem
    identity: tuple[str, str, str] | None = None
    savings_per_package: Decimal = Decimal(0)


@dataclass(frozen=True)
class State:
    mask: int = 0
    stores: tuple[str, ...] = ()
    used: tuple[int, ...] = ()
    total: Decimal = Decimal(0)
    items: tuple[BasketItem, ...] = ()


def stable_items(items: tuple[BasketItem, ...]) -> tuple[tuple[str, str], ...]:
    return tuple((item.food_id, item.product_id) for item in items)


class BasketOptionsService:
    def __init__(self, repository: ProductRepository) -> None:
        self._repository = repository

    def build(self, request: BasketRequest) -> BasketResult:
        foods = request.food_plan.foods
        if len(foods) > 30 or len({f.food_id for f in foods}) != len(foods):
            raise ValidationFailure("invalid_food_requirements")
        groups = {
            group.food_id: group for group in request.search_result.product_matches
        }
        if len(groups) != len(request.search_result.product_matches):
            raise ValidationFailure("duplicate_search_food_id")
        ids = {p.product_id for group in groups.values() for p in group.matches}
        ids.update(
            p
            for pair in request.price_matches.pairs
            for p in (pair.maxi_product_id, pair.competitor_product_id)
        )
        snapshot, products = self._repository.current_by_ids(tuple(sorted(ids)))
        if snapshot is None:
            raise NotFoundError("current_product_snapshot_not_found")
        if snapshot != request.search_result.current_snapshot_date:
            return BasketResult(
                current_snapshot_date=snapshot,
                options=(),
                rejected_reasons=("snapshot_changed_search_again",),
            )
        by_id = {p.product_id: p for p in products}
        preferences = request.shopping_preferences
        distances = {}
        for location in request.store_distances.stores:
            if (
                location.distance_km > preferences.max_distance_km
                or not location.within_max_distance
            ):
                continue
            key = store_identity(location.store)
            if key not in distances or (
                location.distance_km,
                location.store_location_id,
            ) < (distances[key].distance_km, distances[key].store_location_id):
                distances[key] = location
        warnings = list(request.food_plan.warnings + request.search_result.warnings)
        choices: list[list[Choice]] = []
        missing: dict[str, set[str]] = {}
        for food in foods:
            rejected: set[str] = set(food.restriction_reasons)
            available = []
            group = groups.get(food.food_id)
            if not food.restriction_reasons:
                for reference in group.matches if group else ():
                    product = by_id.get(reference.product_id)
                    if product is None:
                        rejected.add("product_not_current_or_not_found")
                        continue
                    score, _ = rank_product(food.food_name, product)
                    if score < MIN_RELEVANCE:
                        rejected.add("insufficient_relevance")
                        continue
                    product_text = normalize(
                        product.name + " " + (product.category_name or "")
                    )
                    if any(
                        concept.tags.intersection(request.food_plan.forbidden_tags)
                        and any(
                            contains(product_text, normalize(alias))
                            for alias in concept.aliases
                        )
                        for concept in FOOD_CONCEPTS.values()
                    ):
                        rejected.add("product_restriction_conflict")
                        continue
                    store = store_identity(product.store)
                    if store not in distances:
                        rejected.add("distance_constraint_or_missing_store")
                        continue
                    quantity = PurchaseQuantityService().calculate(
                        QuantityRequest(
                            food_id=food.food_id,
                            required_amount=food.required_amount,
                            requested_packages=food.requested_packages,
                            product=product,
                            current_snapshot_date=snapshot,
                        )
                    )
                    if quantity.rejected_candidate:
                        rejected.update(quantity.rejected_candidate.reasons)
                        continue
                    purchase = quantity.purchase_candidate
                    assert purchase is not None
                    matches = []
                    # Discover opportunities among retrieved products, in addition to explicit pairs.
                    competitors = {
                        p.product_id
                        for p in by_id.values()
                        if store_identity(p.store) != "maxi"
                    }
                    if store == "maxi":
                        for competitor_id in sorted(competitors):
                            pair = PriceMatchPair(
                                food_id=food.food_id,
                                maxi_product_id=product.product_id,
                                competitor_product_id=competitor_id,
                                packages_requested=purchase.packages_required,
                            )
                            match = PriceMatchService.evaluate(pair, by_id, snapshot)
                            if match.eligible:
                                matches.append(match)
                    best = (
                        min(
                            matches,
                            key=lambda m: (
                                m.matched_unit_price,
                                m.competitor_product_id,
                            ),
                        )
                        if matches
                        else None
                    )
                    item = BasketItem(
                        food_id=food.food_id,
                        product_id=product.product_id,
                        product_name=product.name,
                        store=store,
                        quantity=purchase,
                        match_score=score,
                        line_total=purchase.line_total,
                        competitor_product_id=best.competitor_product_id
                        if best
                        else None,
                    )
                    available.append(
                        Choice(
                            item=item,
                            identity=identity_key(product) if best else None,
                            savings_per_package=product.price - best.matched_unit_price
                            if best
                            else Decimal(0),
                        )
                    )
            choices.append(sorted(available, key=lambda choice: choice.item.product_id))
            missing[food.food_id] = rejected or {"unmatched"}

        # Track the four-package allowance across food lines sharing an identity.
        shared = sorted(
            {
                choice.identity
                for options in choices
                for choice in options
                if choice.identity is not None
                and sum(
                    any(other.identity == choice.identity for other in group)
                    for group in choices
                )
                > 1
            }
        )
        shared_index = {identity: i for i, identity in enumerate(shared)}
        states = {(0, (), (0,) * len(shared)): State(used=(0,) * len(shared))}
        transitions = 0
        for index, available in enumerate(choices):
            next_states = dict(
                states
            )  # Skipping any food remains an explicit alternative.
            for state in states.values():
                for choice in available:
                    transitions += 1
                    if transitions > MAX_OPTIMIZER_TRANSITIONS:
                        return self._limit(snapshot, warnings)
                    stores = tuple(sorted(set(state.stores) | {choice.item.store}))
                    if len(stores) > preferences.max_stores:
                        continue
                    used = list(state.used)
                    remaining = 4
                    if choice.identity in shared_index:
                        counter = shared_index[choice.identity]
                        remaining -= used[counter]
                    count = (
                        min(choice.item.quantity.packages_required, remaining)
                        if choice.identity
                        else 0
                    )
                    if choice.identity in shared_index:
                        used[counter] += count
                    savings = choice.savings_per_package * count
                    item = choice.item.model_copy(
                        update={
                            "line_total": choice.item.quantity.line_total - savings,
                            "price_match_savings": savings,
                            "quantity_matched": count,
                        }
                    )
                    total = state.total + item.line_total
                    budget = request.food_plan.budget
                    if budget is not None and total > budget:
                        continue
                    candidate = State(
                        mask=state.mask | (1 << index),
                        stores=stores,
                        used=tuple(used),
                        total=total,
                        items=state.items + (item,),
                    )
                    key = (candidate.mask, stores, candidate.used)
                    previous = next_states.get(key)
                    if previous is None or (total, stable_items(candidate.items)) < (
                        previous.total,
                        stable_items(previous.items),
                    ):
                        next_states[key] = candidate
                    if len(next_states) > MAX_OPTIMIZER_STATES:
                        return self._limit(snapshot, warnings)
            states = next_states

        # Same food coverage is essential: dropping food is never counted as savings.
        by_mask: dict[int, list[State]] = {}
        for state in states.values():
            by_mask.setdefault(state.mask, []).append(state)
        eligible: list[tuple[State, Decimal | None]] = []
        for state in states.values():
            extra_savings = None
            if len(state.stores) > 1:
                simpler = [
                    s for s in by_mask[state.mask] if len(s.stores) < len(state.stores)
                ]
                if simpler:
                    comparisons = [
                        (
                            other.total - state.total,
                            len(state.stores) - len(other.stores),
                        )
                        for other in simpler
                    ]
                    if any(
                        saved < preferences.minimum_savings_for_extra_store * extra
                        for saved, extra in comparisons
                    ):
                        continue
                    extra_savings = min(saved for saved, _ in comparisons)
                else:
                    # Extra stores are necessary for this coverage, rather than justified by savings.
                    extra_savings = None
            eligible.append((state, extra_savings))
        required_mask = sum(
            1 << i for i, f in enumerate(foods) if f.priority == "required"
        )

        def coverage(state: State) -> tuple[int, int]:
            return (
                -(state.mask & required_mask).bit_count(),
                -(state.mask & ~required_mask).bit_count(),
            )

        def distance(state: State) -> Decimal:
            return sum((distances[s].distance_km for s in state.stores), Decimal(0))

        strategy_keys = {
            "lowest_cost": lambda s: (s.total, len(s.stores), distance(s)),
            "fewest_stores": lambda s: (len(s.stores), s.total, distance(s)),
            "nearest": lambda s: (distance(s), s.total, len(s.stores)),
        }
        order = ["lowest_cost", "fewest_stores", "nearest"]
        if preferences.shopping_priority.value == "convenience":
            order = ["fewest_stores", "nearest", "lowest_cost"]
        results, seen = [], set()
        for strategy in order:
            state, extra = min(
                eligible,
                key=lambda pair: (
                    coverage(pair[0]),
                    strategy_keys[strategy](pair[0]),
                    stable_items(pair[0].items),
                ),
            )
            signature = stable_items(state.items)
            if signature in seen:
                continue
            seen.add(signature)
            required_missing, optional_missing = [], []
            for index, food in enumerate(foods):
                if state.mask & (1 << index):
                    continue
                if choices[index]:
                    reasons = (
                        ("budget_constraint",)
                        if request.food_plan.budget is not None
                        and all(
                            state.total
                            + choice.item.quantity.line_total
                            - min(4, choice.item.quantity.packages_required)
                            * choice.savings_per_package
                            > request.food_plan.budget
                            for choice in choices[index]
                        )
                        else ("store_or_savings_constraint",)
                    )
                else:
                    reasons = tuple(sorted(missing[food.food_id]))
                result = UnfulfilledFood(
                    food_id=food.food_id, food_name=food.food_name, reasons=reasons
                )
                (
                    required_missing
                    if food.priority == "required"
                    else optional_missing
                ).append(result)
            option_warnings = []
            if len(state.stores) > 1 and extra is None:
                option_warnings.append(
                    "extra_stores_required_for_selected_food_coverage"
                )
            results.append(
                BasketOption(
                    option_id=f"option_{len(results) + 1}",
                    strategy_type=strategy,
                    selected_items=state.items,
                    stores=state.stores,
                    store_location_ids=tuple(
                        distances[s].store_location_id for s in state.stores
                    ),
                    total=state.total,
                    budget=request.food_plan.budget,
                    within_budget=True,
                    estimated_savings=sum(
                        (item.price_match_savings for item in state.items), Decimal(0)
                    ),
                    distance_km=distance(state),
                    required_foods_fulfilled=-coverage(state)[0],
                    optional_foods_fulfilled=-coverage(state)[1],
                    unfulfilled_foods=tuple(required_missing),
                    excluded_optional_foods=tuple(optional_missing),
                    complete=not required_missing,
                    extra_store_savings=extra,
                    warnings=tuple(option_warnings),
                )
            )
        return BasketResult(
            current_snapshot_date=snapshot,
            options=tuple(results),
            warnings=tuple(sorted(set(warnings))),
        )

    @staticmethod
    def _limit(snapshot: date, warnings: list[str]) -> BasketResult:
        return BasketResult(
            current_snapshot_date=snapshot,
            options=(),
            rejected_reasons=("optimization_complexity_limit",),
            warnings=tuple(
                sorted(set(warnings + ["reduce_food_or_candidate_count_and_retry"]))
            ),
        )
