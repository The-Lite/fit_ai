# ADR-003: Six-Tool Grocery Agent Architecture

## Status

Accepted

## Context

Fit AI must support more than fixed shopping-list optimization. The agent must eventually use the user's available profile fields, goal, vegetarian flag, budget, store preferences, current product data, and store locations to plan a weekly basket and optimize how it should be purchased.

The current PostgreSQL application tables are:

- `public.users`
- `public.user_locations`
- `public.user_shopping_preferences`
- `public.store_locations`
- `public.epiceries_products`

`public.epiceries_product_checkpoints` is excluded from the agent data model.

## Decision

Fit AI will use six LLM-facing grocery tools:

1. `get_user_context`
2. `plan_weekly_food_basket`
3. `search_current_products`
4. `get_store_distances`
5. `check_price_match`
6. `build_basket_options`

Fit AI will also use internal deterministic Python components:

- `calculate_package_nutrition`
- the integer basket optimizer used by `build_basket_options`

These components are not exposed as additional LLM-facing tools.

The approved flow is:

```text
get_user_context
-> plan_weekly_food_basket
-> search_current_products
-> calculate_package_nutrition
-> check_price_match
-> get_store_distances
-> build_basket_options
-> LLM chooses among valid strategies
```

## Consequences

Benefits:

- nutrition-target planning is separated from product/package purchasing
- eligible canonical foods remain alternatives until current prices are available
- product nutrition and serving/reference data come from the current `epiceries_products` snapshot
- price matching supplies per-package eligibility and savings before optimization
- basket optimization deterministically selects foods, products, package counts, and stores
- the LLM can choose among valid strategies without calculating deterministic values
- model comparisons remain cleaner because tools provide stable calculations

Tradeoffs:

- the service layer has internal catalog, package-nutrition, and optimization steps
- package parsing quality affects downstream optimization
- product rows with missing or incompatible package sizes may need to be rejected or surfaced with warnings

## Contract Location

The source of truth for tool contracts is `docs/architecture/tool-contracts.md`.
