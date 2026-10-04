from __future__ import annotations

from decimal import Decimal

from fit_ai.config.food_catalog import CATALOG_VERSION, FOOD_CONCEPTS, GOAL_STRATEGIES
from fit_ai.domain.common import Amount
from fit_ai.domain.errors import ValidationFailure
from fit_ai.domain.food_matching import normalize, resolve_concept
from fit_ai.domain.planning import FoodInput, FoodPlan, FoodPlanRequest, FoodRequirement

ALLERGY_TAGS = {
    "milk": "milk",
    "dairy": "milk",
    "lait": "milk",
    "egg": "egg",
    "eggs": "egg",
    "oeufs": "egg",
    "fish": "fish",
    "poisson": "fish",
    "soy": "soy",
    "soja": "soy",
    "wheat": "wheat",
    "ble": "wheat",
    "gluten": "gluten",
    "peanut": "peanut",
    "peanuts": "peanut",
    "tree nuts": "nuts",
    "nuts": "nuts",
    "shellfish": "shellfish",
    "sesame": "sesame",
}


class WeeklyFoodPlanningService:
    def plan(self, request: FoodPlanRequest) -> FoodPlan:
        context = request.planning_context
        allergies = {normalize(value) for value in context.allergies}
        restrictions = {normalize(value) for value in context.dietary_restrictions}
        if allergies - ALLERGY_TAGS.keys():
            raise ValidationFailure("unsupported_allergy_tag")
        if restrictions - {
            "vegetarian",
            "vegan",
            "gluten free",
            "dairy free",
            "no fish",
        }:
            raise ValidationFailure("unsupported_dietary_restriction")
        categories = {c.category for c in FOOD_CONCEPTS.values()}
        if (
            set(context.preferred_categories) | set(context.excluded_categories)
        ) - categories:
            raise ValidationFailure("unsupported_food_category")
        forbidden = {ALLERGY_TAGS[a] for a in allergies}
        if request.user_context.user.vegetarian or "vegetarian" in restrictions:
            forbidden.add("meat")
        if "vegan" in restrictions:
            forbidden.update(("meat", "animal"))
        if "gluten free" in restrictions:
            forbidden.add("gluten")
        if "dairy free" in restrictions:
            forbidden.add("milk")
        if context.eats_fish is False or "no fish" in restrictions:
            forbidden.add("fish")
        excluded = {
            resolve_concept(name) or normalize(name) for name in context.excluded_foods
        }
        warnings = ["candidate_foods_are_not_nutritional_requirements"]
        if allergies:
            warnings.append("product_ingredients_and_cross_contact_not_verified")
        if request.foods:
            inputs = request.foods
        else:
            goal = request.user_context.user.goal
            if goal not in GOAL_STRATEGIES:
                goal = "maintenance"
                warnings.append("unknown_goal_using_maintenance_candidates")
            ids = list(GOAL_STRATEGIES[goal])
            preferred = []
            for name in context.preferred_foods:
                key = resolve_concept(name)
                if key is None:
                    raise ValidationFailure("unsupported_preferred_food")
                preferred.append(key)
            ids = list(dict.fromkeys(preferred + ids))
            ids.sort(
                key=lambda key: (
                    FOOD_CONCEPTS[key].category not in context.preferred_categories
                )
            )
            inputs = tuple(
                FoodInput(food_id=key, food_name=FOOD_CONCEPTS[key].name) for key in ids
            )
        if len({food.food_id for food in inputs}) != len(inputs):
            raise ValidationFailure("duplicate_food_id")
        foods = []
        for item in inputs:
            concept_id = resolve_concept(item.food_name)
            concept = FOOD_CONCEPTS.get(concept_id)
            reasons = []
            if concept and concept.tags & forbidden:
                reasons.append("declared_restriction_conflict")
            if (concept_id or normalize(item.food_name)) in excluded:
                reasons.append("excluded_food")
            if concept and concept.category in context.excluded_categories:
                reasons.append("excluded_category")
            if not concept and (forbidden or context.excluded_categories):
                reasons.append("restriction_compatibility_unknown")
            if reasons and not request.foods:
                continue
            amount, packages = None, None
            if item.requested_quantity is not None:
                unit = item.requested_unit
                if unit in {"package", "bag", "bags"}:
                    packages = int(item.requested_quantity)
                else:
                    multiplier = Decimal(1000) if unit in {"kg", "l"} else Decimal(1)
                    normalized_unit = {
                        "kg": "g",
                        "l": "ml",
                        "egg": "unit",
                        "eggs": "unit",
                    }.get(unit, unit)
                    amount = Amount(
                        value=item.requested_quantity * multiplier, unit=normalized_unit
                    )
            foods.append(
                FoodRequirement(
                    **item.model_dump(),
                    concept_id=concept_id,
                    source="user" if request.foods else "default_planner",
                    priority="required" if request.foods else "optional",
                    required_amount=amount,
                    requested_packages=packages,
                    restriction_reasons=tuple(reasons),
                )
            )
        return FoodPlan(
            foods=tuple(foods),
            budget=request.budget
            if request.budget is not None
            else request.user_context.user.budget,
            mode="user" if request.foods else "automatic",
            catalog_version=CATALOG_VERSION,
            planning_context=context,
            warnings=tuple(warnings),
            forbidden_tags=tuple(sorted(forbidden)),
        )
