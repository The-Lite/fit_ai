# Grocery Agent Tool Contracts

These contracts supersede the nutrition-oriented MVP contracts. Domain models
under `src/fit_ai/domain` are the executable schema. All models forbid extra
fields; Decimal values serialize as strings and dates/timestamps as ISO strings.
Tools consume validated request models and return JSON-compatible dictionaries.

## 1. get_user_context

Unchanged: `get_user_context(user_id: int)` reads the existing user, location and
shopping preferences. The output has `user`, `location`, `shopping_preferences`,
`warnings`. Weight is preserved. There are no assumed allergy or preference DB
columns. `FoodPlanRequest` accepts this exact serialized context, restoring the
user ID linkage on location/preferences during model validation.

## 2. plan_weekly_food_basket

Input: `FoodPlanRequest(user_context, foods=(), planning_context={}, budget=None)`.
An explicit budget, including zero, overrides the stored budget.

Each `FoodInput` has `food_id`, `food_name`, optional `requested_quantity` and
`requested_unit` (provided together). Supported units: g, kg, ml, l, unit, egg,
eggs, package, bag, bags. Counts must be whole positive numbers.

`PlanningContext` is declared runtime context: `eats_fish`, `preferred_foods`,
`excluded_foods`, preferred/excluded categories, allergies, dietary restrictions.
Supported restrictions: vegetarian, vegan, gluten free, dairy free, no fish.
Allergy tag vocabulary is centralized in `weekly_food_planning.ALLERGY_TAGS`;
unsupported tags fail rather than being ignored. Empty allergies mean none
declared, not clinical proof of absence.

Output: `FoodPlan(foods, budget, mode, catalog_version, planning_context,
forbidden_tags, warnings)`.

A `FoodRequirement` preserves input fields and adds:

- `source`: user or default_planner;
- `priority`: required or optional, consistent with source;
- `concept_id`: known catalog identity or null;
- `required_amount`: normalized positive g/ml/unit amount or null;
- `requested_packages`: positive integer or null;
- `restriction_reasons`: explicit conflicts that block purchase.

Explicit foods never trigger default replacements. No foods generates ordered,
configurable goal candidates. Aliases are retrieval metadata, not requirements.
Defaults have no physical quantities. The planner never computes nutrition.

## 3. search_current_products

Input: `ProductSearchRequest(food_queries, stores=None, limit_per_food=20)`.
Each query contains `food_id` and `name`; IDs must be unique. Maximum 30 queries,
100 final matches per food. No input snapshot date.

Output: `ProductSearchResult(current_snapshot_date, product_matches,
unmatched_foods, warnings)`. Each group includes `food_id`, original `query`,
`status` (matched/unmatched), and `matches`. A match retains the verified Product
fields and parsed package, adding deterministic `match_score` and `match_reason`.
Missing prices and sizes remain explicit and are assessed during quantity
calculation. Historical rows never qualify.

Repository-selected latest `updated::date`, bilingual concepts, conservative
spelling resolution, bounded SQL retrieval and deterministic ranking are detailed
in `agent-architecture.md`. Minimum relevance: 0.75. Maximum SQL candidates: 300.
No price signal enters ranking. Unknown concepts report missing bilingual
expansion. Candidate cap and unparseable-size warnings are visible.

## Internal purchase quantity service

`QuantityRequest(food_id, product, current_snapshot_date, required_amount=None,
requested_packages=None)`. Only one quantity mode is allowed. This internal
snapshot is repository-derived; the service is not exposed as a public tool.

`PurchaseQuantityService.calculate` returns either `purchase_candidate` or
`rejected_candidate` with reasons. It reparses the real size, rejects stale/missing
price products, and uses `ceil(required_amount/package_amount)` for compatible
physical units. Explicit counts buy that many packages; no quantity buys one.

Candidate fields include packages_required, line_total, quantity_policy,
required_amount, parsed_package, purchased_amount and surplus_amount. Unknown
physical size stays null in package modes. Unknown/ambiguous sizes reject physical
requests. `2 x 500 g` remains unsupported. No nutrition-based quantities.

## 4. get_store_distances

Unchanged: `StoreDistanceRequest(user_location, stores=None, max_distance_km=None)`.
Returns `origin`, store locations, `distance_km`, `within_max_distance`,
`distance_method=lat_lon_haversine`, warnings. Uses the existing location
repository and deterministic Haversine calculation, without routing APIs.

## 5. check_price_match

Input: `PriceMatchRequest(pairs)`, up to 1000 pairs. Each pair contains food_id,
maxi_product_id, competitor_product_id and packages_requested (default one).
It accepts neither caller prices nor a snapshot override. The repository reads
both IDs from its current snapshot, thereby verifying Maxi carries the item.

Output: `PriceMatchResult(current_snapshot_date, price_match_results, warnings)`.
Each evaluation preserves pair IDs/count and reports eligible, reasons,
competitor_store, matched_unit_price, quantity_matched, quantity_not_matched,
estimated_savings, effective_total, source_url. Eligibility requires the approved
competitor, normalized identical name, present identical brand, equal parsed
size/unit, current rows and a lower competitor price. Cross-language semantic
similarity alone cannot establish identical variety.

At most four packages of an identical item get the matched price; remaining
packages use the Maxi price. Individual pair estimates are alternatives and
cannot be summed indiscriminately. The basket service shares the allowance
across selected lines. See `price-matching.md`.

## 6. build_basket_options

Input: `BasketRequest(food_plan, search_result, store_distances,
shopping_preferences, price_matches={pairs: []})`.

- `food_plan` and `search_result` are prior tool outputs.
- `store_distances` accepts the exact distance tool output or domain result.
- `shopping_preferences` is the existing typed ShoppingPreferences, including
  its user_id linkage (available from user_context.user.user_id).
- `price_matches` accepts price-match pairs or the serialized check_price_match
  output; only product references/counts are retained and eligibility is recomputed.

The optimizer rehydrates all referenced products from PostgreSQL, rechecks
relevance, applies quantity calculations internally and discovers additional
strict Maxi matches among retrieved candidates. It never trusts supplied product
prices, scores, parsed sizes or savings. A changed snapshot requires a new search.

Output: `BasketResult(current_snapshot_date, options, rejected_reasons, warnings,
algorithm)`. Each BasketOption contains strategy_type, selected_items, stores,
store_location_ids, total, budget, within_budget, estimated_savings, distance_km,
required/optional coverage, unfulfilled_foods, excluded_optional_foods, complete,
extra_store_savings and warnings. Items include actual product ID/name/store,
PurchaseCandidate quantity details, score, adjusted line_total, matched count,
savings and competitor evidence ID.

Budget is hard. Relevance filtering precedes cost comparison. Maximize required
then optional coverage; select cost/store/distance alternatives deterministically.
Unknown physical quantities are never invented. Duplicate strategy assignments
are removed. Empty baskets are representable with explicit missing required foods.

Exact DP is bounded operationally to 250,000 states/3,000,000 transitions and is
exact only within the retrieved candidate pool and deterministic policies.
Oversized requests return no options and `optimization_complexity_limit`.
Extra-store savings compare identical food coverage with feasible simpler store
sets; necessary extra stores without a simpler baseline carry an explicit warning.
No nutrition satisfaction is claimed.

## Failure and trust boundaries

Domain validation rejects malformed inputs. Expected repository/service failures
use FitAiError subclasses; the future agent adapter must expose safe messages,
not chained SQL/connection details. Repositories perform SELECTs and read-only
transaction settings only. Tool outputs belong in application-managed state;
user restrictions/preferences remain application context, not inferred secrets.
