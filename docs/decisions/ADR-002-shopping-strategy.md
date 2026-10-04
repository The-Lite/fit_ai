# ADR-002: Shopping Strategy Selection

## Status

Proposed

## Context

Users may value different tradeoffs when shopping for groceries. Some users want the lowest price. Others want fewer stores, shorter travel, better price matching, or budget certainty.

Fit AI stores user preferences including:

- `shopping_priority`
- `max_stores`
- `max_distance_km`
- `minimum_savings_for_extra_store`

The shopping strategy must use already-calculated purchase candidates, current product data, price-match results, and store distances.

## Decision

Fit AI will generate deterministic candidate plans and allow the LLM to choose among valid strategies.

Python tools will enforce hard constraints. The LLM may choose and explain tradeoffs only after receiving structured candidate plans.

The final approved flow is:

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

`calculate_package_nutrition` is an internal deterministic service, not an LLM-facing tool. The deterministic optimizer used by `build_basket_options` selects canonical foods, real products, and integer package counts.

## Strategy Inputs

Strategy selection should consider:

- total cart price
- total estimated savings
- number of stores
- distance to each store
- user max distance
- user max stores
- minimum savings required for an extra store
- price-match opportunities
- budget status
- unavailable or substituted items
- nutrition targets and nutrition supplied per package
- selected canonical foods and integer package quantities

## Strategy Types

Initial strategy candidates may include:

- lowest price
- fewest stores
- nearest viable stores
- best savings within constraints
- Maxi price-match focused
- budget-first

## Consequences

Benefits:

- clear separation between computation and judgment
- easier model comparison
- strategies can be evaluated consistently
- user-facing explanations remain flexible

Tradeoffs:

- candidate generation must be strong enough for the LLM to compare
- strategy selection requires structured scoring metadata
