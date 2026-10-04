# Grocery Agent Architecture

Fit AI's MVP is a goal-aware grocery shopping assistant. It has no nutrition
optimization, physiological food formulas, calorie targets, nutrient APIs or
nutrition-column dependency. A basket is not a nutritional prescription.

## Flow

```text
LLM extracts foods, explicit quantities and constraints
  -> get_user_context
  -> plan_weekly_food_basket
  -> search_current_products
  -> internal purchase quantity calculation
  -> check_price_match + get_store_distances
  -> build_basket_options
  -> LLM explains valid alternatives and any missing foods
```

Exactly six functions appear in `fit_ai.tools.PUBLIC_TOOLS`. Quantity calculation
and basket optimization remain internal Python operations. The conversational
agent, Vercel AI Gateway orchestration and MLflow evaluation are separate work.

## Layers and reused components

Pydantic domain models validate contracts. Thin tools serialize services' results.
Services implement planning, ranking, quantity arithmetic, price matching and
optimization. Repositories own parameterized SQL and verified PostgreSQL mappings.
Existing user context, store locations, Haversine distances, database settings,
package parsing and Decimal quantity arithmetic are reused.

The only application tables are `users`, `user_locations`,
`user_shopping_preferences`, `store_locations`, and `epiceries_products` in public.
No schema or data writes are part of the MVP. `epiceries_product_checkpoints`
is not used.

## Food planning

`config/food_catalog.py` contains version `mvp-1`: EN/FR concepts, category/tag
metadata, exclusions, ordered goal strategies and search settings. No nutrients
are stored in this catalog. Explicit foods retain their IDs, names, quantities,
user source and required priority. An empty list selects optional defaults for
muscle gain, maintenance or weight loss. Unknown goals use maintenance with a
warning. Preferred foods/categories move earlier; exclusions and restrictions
filter candidates before search. Weight remains in the existing user context
and is never used to derive amounts.

The verified schema stores a vegetarian flag, but no detailed food preferences,
allergies or restrictions. `PlanningContext(source='runtime')` represents declared
values without claiming database persistence. Unsupported restrictions/allergies
fail explicitly. Explicit requests conflicting with restrictions remain visible,
blocked and unfulfilled, rather than silently replaced. Catalog tags and visible
product words do not establish ingredient or cross-contact safety.

## Retrieval

Python normalizes case, accents, punctuation and ligatures, resolves known food
concepts, expands bilingual aliases, and conservatively resolves spelling errors.
Alias expansion never creates additional requirements. Unknown concepts receive
literal retrieval plus a warning that bilingual expansion is unavailable; extend
the central vocabulary to add coverage. No LLM translation or similarity scores.

The repository retrieves at most 300 candidates per food, in a read-only
repeatable-read transaction for the entire batch. Every SQL query contains the
latest `MAX(updated::date)` predicate; no public search accepts a snapshot date.
SQL normalizes names/categories/brands without extensions, applies word/token
predicates, and orders by textual signals and product ID before LIMIT. It never
orders candidate retrieval by cheapest price. The service filters stale rows,
rejects prepared/flavour contexts and ranks names deterministically. Category
matches strengthen identity but cannot independently establish a match. Brand is
a retrieval signal only. The default final limit is 20, maximum 100 per food.

Scores: normalized exact alias 1.00, whole phrase 0.94, all tokens 0.88; fuzzy
name-window similarity >=0.86 contributes similarity *0.90. A matching category
adds 0.02, capped at 1.00. Minimum accepted score is 0.75. Equal scores use product
ID, not price. Scores are relevance signals, not calibrated probabilities.
Candidates below the threshold are excluded before price optimization.

`pg_trgm` was absent on 2026-09-20. Only `plpgsql` was installed. The implementation
uses no extension, index or schema changes. It does not load the whole catalog
into Python. SQL may still scan rows because no indexes were added. Broad-query
candidate caps are reported; global database recall is not guaranteed.

## Purchasing and optimization

The existing size parser safely normalizes simple g/kg, ml/l and count formats.
Explicit physical quantities use ceiling division. Explicit package/bag counts
are integers. Otherwise select one purchasable package. Missing/ambiguous size
never acquires an invented physical quantity: physical requests are rejected;
package/default requests may have unknown purchased amount. Multipacks remain
unparsed. Money and quantity arithmetic use Decimal; no weight-based formulas.

Price matching uses strict name, brand and parsed-size equality, current product
membership and the approved competitor list. Food-search similarity cannot prove
identity. Basket calculations re-read product IDs and recompute relevance,
quantities and price matching rather than trusting caller prices or scores.
A changed snapshot returns an instruction to search again.

The optimizer uses exact dynamic programming over the retrieved candidate pool,
not over every product in PostgreSQL. States retain selected food IDs, store set,
shared price-match allowances and lowest cost. It maximizes required coverage,
then optional coverage, under the hard budget and store/distance constraints.
It produces deduplicated lowest-cost, fewest-store and nearest alternatives.
Convenience preferences order the fewest-store option first; balanced/savings
order lowest cost first. There is no LLM-generated optimization score.

For the same selected food coverage, an extra store must save at least the
configured minimum per extra store against feasible simpler alternatives.
When only multiple stores can provide that coverage, this is explicitly marked
`extra_stores_required_for_selected_food_coverage`; no imaginary savings baseline
is invented. Competitor evidence for a Maxi match does not require a store visit.
Distance is the sum of origin-to-selected-store Haversine distances, not a route.

Operational limits are centralized: 250,000 states and 3,000,000 transitions.
Exceeding either returns `optimization_complexity_limit`, no partial basket and
no false optimality claim. Missing required foods and excluded defaults are
reported separately. An empty or partial basket never claims full required-food
coverage. Nutrition can later extend planning/quantities, but is not implemented.
