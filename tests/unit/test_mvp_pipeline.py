from datetime import date, datetime, timezone
from decimal import Decimal

import pytest
from pydantic import ValidationError

from fit_ai.config.food_catalog import CANDIDATE_LIMIT, FOOD_CONCEPTS, MIN_RELEVANCE
from fit_ai.domain.baskets import BasketRequest
from fit_ai.domain.errors import ValidationFailure
from fit_ai.domain.food_matching import (
    normalize,
    query_aliases,
    rank_product,
    resolve_concept,
)
from fit_ai.domain.planning import FoodInput, FoodPlanRequest, PlanningContext
from fit_ai.domain.price_matching import PriceMatchPair, PriceMatchRequest
from fit_ai.domain.products import (
    FoodQuery,
    Product,
    ProductSearchRequest,
    QuantityRequest,
)
from fit_ai.domain.stores import StoreDistance, StoreDistanceResult
from fit_ai.domain.users import ShoppingPreferences, User, UserContext, UserLocation
from fit_ai.services.basket_options import BasketOptionsService
from fit_ai.services.price_matching import PriceMatchService
from fit_ai.services.product_search import ProductSearchService
from fit_ai.services.purchase_quantities import PurchaseQuantityService
from fit_ai.services.weekly_food_planning import WeeklyFoodPlanningService
from fit_ai.tools import PUBLIC_TOOLS
from fit_ai.tools.grocery import (
    build_basket_options,
    check_price_match,
    plan_weekly_food_basket,
)

SNAPSHOT = date(2026, 9, 13)
NOW = datetime(2026, 9, 13, tzinfo=timezone.utc)


def product(
    pid="p1", name="Chicken breast", store="maxi", price="8", size="900g", **kwargs
):
    return Product(
        product_id=pid,
        name=name,
        store=store,
        price=price,
        size=size,
        brand="Brand",
        updated=NOW,
        loaded_at=NOW,
        **kwargs,
    )


class Repository:
    def __init__(self, products):
        self.products = tuple(products)
        self.limit = None

    def search_batch(self, queries, stores, limit):
        self.limit = limit
        return SNAPSHOT, tuple(self.products[:limit] for _ in queries)

    def current_by_ids(self, ids):
        return SNAPSHOT, tuple(p for p in self.products if p.product_id in ids)


def context(goal="muscle_gain", budget=80):
    return UserContext(
        user=User(
            user_id=1,
            username="Test",
            age=30,
            weight_kg=80,
            height_cm=180,
            goal=goal,
            vegetarian=False,
            budget=budget,
        ),
        location=UserLocation(user_id=1, latitude=45, longitude=-73),
        shopping_preferences=ShoppingPreferences(
            user_id=1,
            shopping_priority="balanced",
            max_stores=2,
            max_distance_km=10,
            minimum_savings_for_extra_store=2,
        ),
    )


def distances():
    return StoreDistanceResult(
        origin_latitude=45,
        origin_longitude=-73,
        stores=tuple(
            StoreDistance(
                store_location_id=i,
                store=store,
                store_name=store,
                latitude=45,
                longitude=-73,
                distance_km=i,
                within_max_distance=True,
            )
            for i, store in enumerate(("maxi", "walmart", "metro"), 1)
        ),
    )


def plan(foods=(), budget=80, runtime=None):
    return WeeklyFoodPlanningService().plan(
        FoodPlanRequest(
            user_context=context(budget=budget),
            foods=foods,
            planning_context=runtime or PlanningContext(),
        )
    )


def basket_request(food_plan, products, **overrides):
    search = ProductSearchService(Repository(products)).search(
        ProductSearchRequest(
            food_queries=tuple(
                FoodQuery(food_id=f.food_id, name=f.food_name) for f in food_plan.foods
            )
        )
    )
    values = {
        "food_plan": food_plan,
        "search_result": search,
        "store_distances": distances(),
        "shopping_preferences": context().shopping_preferences,
    }
    values.update(overrides)
    return BasketRequest(**values)


@pytest.mark.parametrize(
    ("query", "name"),
    [
        ("chicken", "Fresh Chicken Breast"),
        ("rice", "Long Grain Rice"),
        ("chicken", "Poitrine de poulet"),
        ("rice", "Riz basmati"),
        ("eggs", "Œufs frais"),
        ("poulet", "Chicken Thighs"),
        ("riz", "Rice"),
        ("oeufs", "Large Eggs"),
        ("chicken breast", "Boneless Chicken Breast"),
        ("chicken breast", "Poitrine de poulet"),
        ("poitrine de poulet", "Chicken Breast"),
        ("chiken", "Poitrine de poulet"),
        ("poulett", "Chicken"),
        ("saumom", "Salmon"),
        ("épinards", "Spinach"),
    ],
)
def test_bilingual_specific_and_typo_retrieval(query, name):
    result = ProductSearchService(Repository([product(name=name)])).search(
        ProductSearchRequest(food_queries=(FoodQuery(food_id="food", name=query),))
    )
    assert result.product_matches[0].status == "matched"
    assert result.product_matches[0].matches[0].match_score >= MIN_RELEVANCE


@pytest.mark.parametrize(
    "name",
    [
        "Chicken Noodle Soup",
        "Chicken Gravy",
        "Chicken Seasoning",
        "Chicken-Flavoured Chips",
        "Soupe au poulet",
        "Sauce au poulet",
        "Assaisonnement au poulet",
        "Chicken Dog Food",
    ],
)
def test_irrelevant_cheap_products_are_excluded(name):
    assert rank_product("chicken", product(name=name, price="0.01"))[0] < MIN_RELEVANCE


def test_specific_concept_does_not_accept_generic_food():
    assert (
        rank_product("chicken breast", product(name="Chicken thighs"))[0]
        < MIN_RELEVANCE
    )
    assert rank_product("apple", product(name="Pommes de terre"))[0] < MIN_RELEVANCE


def test_aliases_accents_unknown_and_price_independent_stable_order():
    assert normalize("Œufs ÉPINARDS") == "oeufs epinards"
    assert query_aliases("chiken") == query_aliases("poulet")
    assert resolve_concept("saumom") == "salmon"
    products = [
        product("b", name="Rice", price="1"),
        product("a", name="Rice", price="10"),
    ]
    request = ProductSearchRequest(
        food_queries=(
            FoodQuery(food_id="r", name="rice"),
            FoodQuery(food_id="u", name="unknown food"),
        )
    )
    repo = Repository(products)
    first = ProductSearchService(repo).search(request)
    second = ProductSearchService(Repository(reversed(products))).search(request)
    assert first == second
    assert [p.product_id for p in first.product_matches[0].matches] == ["a", "b"]
    assert first.unmatched_foods == ("u",)
    assert repo.limit == CANDIDATE_LIMIT


def test_stale_rows_defensively_rejected():
    stale = product().model_copy(
        update={"updated": datetime(2025, 1, 1, tzinfo=timezone.utc)}
    )
    result = ProductSearchService(Repository([stale])).search(
        ProductSearchRequest(food_queries=(FoodQuery(food_id="c", name="chicken"),))
    )
    assert result.unmatched_foods == ("c",)


def test_explicit_foods_and_quantities_preserved_without_defaults():
    result = plan(
        (
            FoodInput(
                food_id="c",
                food_name="chicken",
                requested_quantity=2,
                requested_unit="kg",
            ),
        )
    )
    assert len(result.foods) == 1
    food = result.foods[0]
    assert food.source == "user" and food.priority == "required"
    assert food.required_amount.value == 2000
    assert food.requested_quantity == 2 and food.requested_unit == "kg"


def test_automatic_goal_strategy_filters_fish_and_allergies_without_nutrition():
    result = plan(
        runtime=PlanningContext(
            eats_fish=False, allergies=("milk",), excluded_foods=("eggs",)
        )
    )
    assert result.mode == "automatic" and result.foods
    for food in result.foods:
        assert food.priority == "optional" and food.source == "default_planner"
        assert not FOOD_CONCEPTS[food.concept_id].tags & {"fish", "milk", "egg"}
        assert food.required_amount is None
    assert "nutrition" not in type(result).model_fields


def test_explicit_restriction_conflict_is_visible_not_replaced():
    result = plan(
        (FoodInput(food_id="s", food_name="salmon"),),
        runtime=PlanningContext(eats_fish=False),
    )
    assert result.foods[0].food_name == "salmon"
    assert result.foods[0].restriction_reasons == ("declared_restriction_conflict",)


def test_unsupported_restrictions_fail_instead_of_ignoring():
    with pytest.raises(ValidationFailure, match="unsupported"):
        plan(runtime=PlanningContext(dietary_restrictions=("unknown",)))


def test_default_and_explicit_bag_quantity_policies():
    unknown = product(size="2 x 500 g")
    default = PurchaseQuantityService().calculate(
        QuantityRequest(food_id="c", product=unknown, current_snapshot_date=SNAPSHOT)
    )
    assert default.purchase_candidate.packages_required == 1
    assert default.purchase_candidate.purchased_amount is None
    assert default.purchase_candidate.quantity_policy == "default_one_package"
    bag_plan = plan(
        (
            FoodInput(
                food_id="r",
                food_name="rice",
                requested_quantity=2,
                requested_unit="bags",
            ),
        )
    )
    food = bag_plan.foods[0]
    result = PurchaseQuantityService().calculate(
        QuantityRequest(
            food_id="r",
            requested_packages=food.requested_packages,
            product=product(),
            current_snapshot_date=SNAPSHOT,
        )
    )
    assert result.purchase_candidate.packages_required == 2
    with pytest.raises(ValidationError):
        FoodInput(
            food_id="r",
            food_name="rice",
            requested_quantity="1.5",
            requested_unit="bags",
        )


def test_price_match_cap_and_normalized_size():
    maxi, competitor = (
        product(size="1kg", price="10"),
        product("p2", store="Super C", size="1000g", price="6"),
    )
    result = PriceMatchService(Repository([maxi, competitor])).check(
        PriceMatchRequest(
            pairs=(
                PriceMatchPair(
                    food_id="c",
                    maxi_product_id="p1",
                    competitor_product_id="p2",
                    packages_requested=6,
                ),
            )
        )
    )
    match = result.price_match_results[0]
    assert match.eligible
    assert match.quantity_matched == 4 and match.quantity_not_matched == 2
    assert match.estimated_savings == 16 and match.effective_total == 44


@pytest.mark.parametrize(
    ("change", "reason"),
    [
        ({"brand": None}, "missing_competitor_brand"),
        ({"size": None}, "missing_competitor_size"),
        ({"name": "Poitrine de poulet"}, "identical_product_not_proven"),
        ({"store": "other"}, "ineligible_competitor"),
        ({"size": "500g"}, "size_mismatch"),
        ({"price": Decimal(20)}, "no_price_advantage"),
        (
            {"updated": datetime(2020, 1, 1, tzinfo=timezone.utc)},
            "stale_competitor_product",
        ),
    ],
)
def test_price_match_is_stricter_than_search(change, reason):
    competitor = product("p2", store="walmart", price="4").model_copy(update=change)
    result = PriceMatchService.evaluate(
        PriceMatchPair(food_id="c", maxi_product_id="p1", competitor_product_id="p2"),
        {"p1": product(), "p2": competitor},
        SNAPSHOT,
    )
    assert not result.eligible and reason in result.reasons


def test_budget_preserves_required_before_optional_and_reports_missing():
    required = plan((FoodInput(food_id="c", food_name="chicken"),), budget=9)
    optional = plan().foods
    required = required.model_copy(
        update={
            "foods": required.foods + tuple(f for f in optional if f.food_id == "rice")
        }
    )
    products = [product(price="8"), product("rice", name="Rice", price="3")]
    result = BasketOptionsService(Repository(products)).build(
        basket_request(required, products)
    )
    chosen = result.options[0]
    assert chosen.total == 8 and chosen.required_foods_fulfilled == 1
    assert chosen.excluded_optional_foods[0].food_id == "rice"
    assert chosen.complete
    scarce = plan((FoodInput(food_id="c", food_name="chicken"),), budget=7)
    unavailable = (
        BasketOptionsService(Repository(products))
        .build(basket_request(scarce, products))
        .options[0]
    )
    assert not unavailable.complete and unavailable.unfulfilled_foods[0].reasons == (
        "budget_constraint",
    )


def test_optimizer_uses_cheaper_relevant_product_and_enforces_amount():
    foods = plan(
        (
            FoodInput(
                food_id="c",
                food_name="chicken",
                requested_quantity=2,
                requested_unit="kg",
            ),
        ),
        budget=30,
    )
    products = [
        product("expensive", price="10"),
        product("cheap", price="8"),
        product("soup", name="Chicken Soup", price="1"),
    ]
    result = (
        BasketOptionsService(Repository(products))
        .build(basket_request(foods, products))
        .options[0]
    )
    assert result.total == 24
    assert result.selected_items[0].quantity.packages_required == 3
    assert result.selected_items[0].product_id == "cheap"


def test_extra_store_savings_and_distance_constraints():
    foods = plan(
        (
            FoodInput(food_id="c", food_name="chicken"),
            FoodInput(food_id="r", food_name="rice"),
        )
    )
    products = [
        product("c", price="8"),
        product("r1", name="Rice", price="4"),
        product("r2", name="Rice", price="3", store="walmart").model_copy(
            update={"brand": "Other"}
        ),
    ]
    result = (
        BasketOptionsService(Repository(products))
        .build(basket_request(foods, products))
        .options[0]
    )
    assert result.stores == ("maxi",) and result.total == 12
    preferences = context().shopping_preferences.model_copy(
        update={"minimum_savings_for_extra_store": Decimal(1)}
    )
    result = (
        BasketOptionsService(Repository(products))
        .build(basket_request(foods, products, shopping_preferences=preferences))
        .options[0]
    )
    assert result.total == 11 and result.stores == ("maxi", "walmart")
    far = distances().model_copy(
        update={
            "stores": tuple(
                s.model_copy(update={"distance_km": Decimal(20)})
                for s in distances().stores
            )
        }
    )
    result = (
        BasketOptionsService(Repository(products))
        .build(basket_request(foods, products, store_distances=far))
        .options[0]
    )
    assert not result.selected_items and not result.complete


def test_price_match_cap_shared_across_alias_requirements_and_tampered_totals():
    foods = plan(
        (
            FoodInput(
                food_id="a",
                food_name="chicken",
                requested_quantity=3,
                requested_unit="package",
            ),
            FoodInput(
                food_id="b",
                food_name="poulet",
                requested_quantity=3,
                requested_unit="package",
            ),
        )
    )
    products = [product(price="10"), product("p2", store="walmart", price="6")]
    request = basket_request(foods, products)
    only_maxi = distances().model_copy(update={"stores": (distances().stores[0],)})
    request = request.model_copy(update={"store_distances": only_maxi})
    result = BasketOptionsService(Repository(products)).build(request).options[0]
    assert result.total == 44 and result.estimated_savings == 16
    assert sum(i.quantity_matched for i in result.selected_items) == 4


def test_snapshot_change_and_complexity_limit_are_explicit(monkeypatch):
    foods = plan((FoodInput(food_id="c", food_name="chicken"),))
    products = [product()]
    request = basket_request(foods, products)
    changed = request.search_result.model_copy(
        update={"current_snapshot_date": date(2020, 1, 1)}
    )
    service = BasketOptionsService(Repository(products))
    assert service.build(
        request.model_copy(update={"search_result": changed})
    ).rejected_reasons == ("snapshot_changed_search_again",)
    monkeypatch.setattr("fit_ai.services.basket_options.MAX_OPTIMIZER_TRANSITIONS", 0)
    limited = service.build(request)
    assert not limited.options and limited.rejected_reasons == (
        "optimization_complexity_limit",
    )


def test_all_six_tool_adapters_pipeline_and_serialization():
    assert {f.__name__ for f in PUBLIC_TOOLS} == {
        "get_user_context",
        "plan_weekly_food_basket",
        "search_current_products",
        "get_store_distances",
        "check_price_match",
        "build_basket_options",
    }
    products = [product(), product("p2", store="walmart", price="5")]
    payload = plan_weekly_food_basket(
        FoodPlanRequest(
            user_context=context(), foods=(FoodInput(food_id="c", food_name="chicken"),)
        )
    )
    from fit_ai.domain.planning import FoodPlan

    food_plan = FoodPlan.model_validate(payload)
    matches = check_price_match(
        PriceMatchRequest(
            pairs=(
                PriceMatchPair(
                    food_id="c", maxi_product_id="p1", competitor_product_id="p2"
                ),
            )
        ),
        service=PriceMatchService(Repository(products)),
    )
    request = basket_request(food_plan, products, price_matches=matches)
    result = build_basket_options(
        request, service=BasketOptionsService(Repository(products))
    )
    assert result["options"][0]["total"] == "5"
