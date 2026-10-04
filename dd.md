# Corrected Architecture And Affected Contract Changes

This update fixes the dependency issue between purchase quantity calculation, price matching, and basket optimization.

The six LLM-facing tools remain:

1. `get_user_context`
2. `plan_weekly_food_basket`
3. `search_current_products`
4. `get_store_distances`
5. `check_price_match`
6. `build_basket_options`

`calculate_purchase_quantities` is not a seventh LLM-facing tool. It is an internal deterministic Python service.

The approved PostgreSQL application tables remain:

- `public.users`
- `public.user_locations`
- `public.user_shopping_preferences`
- `public.store_locations`
- `public.epiceries_products`

Ignore `public.epiceries_product_checkpoints`.

## Corrected Data Flow

```text
get_user_context
-> 
plan_weekly_food_basket
-> 
search_current_products
-> 
calculate_purchase_quantities
-> 
check_price_match
-> 
get_store_distances
-> 
build_basket_options
-> 
LLM chooses among valid strategies
```

## Key Correction

`check_price_match` requires `packages_required`, but `check_price_match` happens before `build_basket_options`.

Therefore, `build_basket_options` must not be responsible for calculating `packages_required`.

Purchase quantities must be calculated by an internal deterministic service immediately after `search_current_products` and before `check_price_match`.

## Internal Service: `calculate_purchase_quantities`

### Responsibility

Convert planned food requirements into purchasable package quantities for each real product candidate returned by `search_current_products`.

This service bridges:

```text
food requirement: "need approximately X grams/servings/units"
```

and:

```text
purchase quantity: "buy N packages of this actual product"
```

### LLM Exposure

Not exposed to the LLM.

### Inputs

```json
{
  "food_requirements": [
    {
      "food_id": "string",
      "name": "string",
      "required_amount": {
        "value": "decimal",
        "unit": "string"
      }
    }
  ],
  "product_matches": [
    {
      "food_id": "string",
      "required_amount": {
        "value": "decimal",
        "unit": "string"
      },
      "matches": [
        {
          "product_id": "string",
          "name": "string",
          "brand": "string | null",
          "size": "string | null",
          "unit_price": "string | null",
          "price": "decimal | null",
          "store": "string",
          "updated_date": "date",
          "parsed_package": {
            "amount": "decimal | null",
            "unit": "string | null",
            "source_field": "size | unit_price | null"
          }
        }
      ]
    }
  ],
  "current_snapshot_date": "date"
}
```

### Outputs

```json
{
  "purchase_candidates": [
    {
      "food_id": "string",
      "required_amount": {
        "value": "decimal",
        "unit": "string"
      },
      "product_id": "string",
      "name": "string",
      "brand": "string | null",
      "size": "string | null",
      "store": "string",
      "price": "decimal",
      "unit_price": "string | null",
      "updated_date": "date",
      "parsed_package": {
        "amount": "decimal",
        "unit": "string",
        "source_field": "size | unit_price"
      },
      "packages_required": "integer",
      "purchased_amount": {
        "value": "decimal",
        "unit": "string"
      },
      "surplus_amount": {
        "value": "decimal",
        "unit": "string"
      },
      "quantity_status": "ok | incompatible_units | missing_package_size | missing_price | stale_product"
    }
  ],
  "rejected_candidates": [
    {
      "food_id": "string",
      "product_id": "string | null",
      "reasons": ["string"]
    }
  ],
  "warnings": ["string"]
}
```

### Deterministic Logic

For compatible fixed-size packages:

```text
packages_required = ceil(required_amount / package_amount)
purchased_amount = packages_required * package_amount
surplus_amount = purchased_amount - required_amount
```

Rules:

- Use only actual product/package information returned by `search_current_products`.
- Use `parsed_package.amount` and `parsed_package.unit`.
- Calculate package quantities only when `required_amount.unit` and `parsed_package.unit` are compatible.
- Reject or flag candidates with missing package size.
- Reject or flag candidates with missing price.
- Reject any product whose `updated_date` does not match `current_snapshot_date`.
- Do not ask the LLM to infer package sizes or quantities.

### PostgreSQL Tables Used

None directly.

This service consumes already-retrieved current product rows from `search_current_products`.

## Affected Contract Change: `search_current_products`

`search_current_products` still searches only current-snapshot products from `public.epiceries_products`.

It must still enforce:

```sql
updated::date = (
  SELECT MAX(updated::date)
  FROM public.epiceries_products
)
```

But its responsibility stops at returning real product candidates and parsed package metadata when available.

It does not calculate:

- `packages_required`
- `purchased_amount`
- `surplus_amount`
- basket totals
- price-match eligibility

Its output becomes input to internal `calculate_purchase_quantities`.

## Affected Contract Change: `check_price_match`

### Responsibility

Evaluate Maxi price-match eligibility and savings deterministically using purchase candidates that already include calculated package quantities.

### Input Change

`check_price_match` consumes `purchase_candidates` from internal `calculate_purchase_quantities`.

```json
{
  "purchase_candidates": [
    {
      "food_id": "string",
      "required_amount": {
        "value": "decimal",
        "unit": "string"
      },
      "product_id": "string",
      "name": "string",
      "brand": "string | null",
      "size": "string | null",
      "store": "string",
      "price": "decimal",
      "unit_price": "string | null",
      "updated_date": "date",
      "parsed_package": {
        "amount": "decimal",
        "unit": "string",
        "source_field": "size | unit_price"
      },
      "packages_required": "integer",
      "purchased_amount": {
        "value": "decimal",
        "unit": "string"
      },
      "surplus_amount": {
        "value": "decimal",
        "unit": "string"
      }
    }
  ],
  "current_snapshot_date": "date"
}
```

### Deterministic Logic

- Use only purchase candidates from the current snapshot.
- Use `packages_required` from internal quantity planning.
- Apply maximum 4 matched packages per identical item.
- Calculate savings only for matched packages.
- Do not calculate package quantities inside `check_price_match`.

### Missing Brand Or Size

Price matching requires proof of same brand and same size or weight.

If brand or size is missing on either the Maxi product or the competitor product:

- mark the match `eligible: false`
- do not ask the LLM to infer missing values
- include a specific reason such as:
  - `missing_maxi_brand`
  - `missing_competitor_brand`
  - `missing_maxi_size`
  - `missing_competitor_size`
  - `identical_product_not_proven`

Because `public.epiceries_products` has no `variety`, `valid_from`, `valid_to`, or `valid_flyer_source` fields, the MVP must not invent them.

Current offer validity is determined only by membership in the latest `updated::date` snapshot.

## Affected Contract Change: `get_store_distances`

`get_store_distances` remains an LLM-facing tool and still calculates distances using only latitude and longitude.

In the corrected flow, it runs after `check_price_match` and before `build_basket_options`.

This ordering allows `build_basket_options` to receive both:

- price-match-adjusted purchase candidates
- deterministic store distances

## Affected Contract Change: `build_basket_options`

### Responsibility

Generate valid deterministic basket/store strategy candidates from already-calculated purchase candidates, price-match results, store distances, and user preferences.

It does not calculate purchase quantities.

### Input Change

`build_basket_options` should consume `purchase_candidates` from internal `calculate_purchase_quantities`.

```json
{
  "purchase_candidates": [
    {
      "food_id": "string",
      "required_amount": {
        "value": "decimal",
        "unit": "string"
      },
      "product_id": "string",
      "name": "string",
      "brand": "string | null",
      "size": "string | null",
      "store": "string",
      "price": "decimal",
      "unit_price": "string | null",
      "updated_date": "date",
      "parsed_package": {
        "amount": "decimal",
        "unit": "string",
        "source_field": "size | unit_price"
      },
      "packages_required": "integer",
      "purchased_amount": {
        "value": "decimal",
        "unit": "string"
      },
      "surplus_amount": {
        "value": "decimal",
        "unit": "string"
      }
    }
  ],
  "price_match_results": {},
  "store_distances": {},
  "user_context": {
    "user": {
      "budget": "decimal | null"
    },
    "shopping_preferences": {
      "shopping_priority": "string",
      "max_stores": "integer",
      "max_distance_km": "number",
      "minimum_savings_for_extra_store": "decimal"
    }
  }
}
```

### Removed Responsibility

Remove these responsibilities from `build_basket_options`:

- calculating `packages_required`
- calculating `purchased_amount`
- calculating `surplus_amount`
- parsing package sizes

Those belong to internal `calculate_purchase_quantities`.

### Remaining Deterministic Logic

`build_basket_options` still deterministically calculates:

- line totals using `price`, `effective_price`, and `packages_required`
- price-match-adjusted totals using `check_price_match` output
- store totals
- basket totals
- budget compliance using `public.users.budget` from `get_user_context`
- max store compliance
- max distance compliance
- minimum savings required for an extra store
- valid strategy candidates

Strategy candidates include:

- lowest price
- fewest stores
- nearest
- best savings within constraints
- Maxi price-match focused
- budget-first

The LLM chooses among valid strategies returned by `build_basket_options`; it does not calculate totals, quantities, distances, budget compliance, or price-match eligibility.
