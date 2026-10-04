# Price Matching

## MVP Scope

The MVP supports Maxi price matching.

## Eligible Competitors

Maxi price matching may use offers from:

- Super C
- Walmart
- Metro
- IGA
- Provigo

## Eligibility Rules

A competitor offer is eligible only when all of the following are true:

- competitor is eligible
- same brand
- same size or weight
- same variety when it can be proven from available product data
- Maxi carries the product
- competitor offer is currently valid
- no more than 4 units of the same item are matched

## Deterministic Enforcement

Price-match eligibility must be evaluated by Python services and tools.

The LLM may explain why a match is or is not eligible, but only using structured results returned by the price-matching tool.

## Current Data Limits

The current `public.epiceries_products` table has `name`, `brand`, `size`, `price`, `unit_price`, `store`, `updated`, and related product fields. It does not have separate `variety`, `valid_from`, `valid_to`, or `valid_flyer_source` columns.

For the MVP, offer validity is determined only by membership in the latest `updated::date` snapshot:

```sql
updated::date = (
  SELECT MAX(updated::date)
  FROM public.epiceries_products
)
```

The system must not invent missing flyer validity fields.

When brand or size is missing on either the Maxi product or competitor product, eligibility cannot be proven. The tool must return `eligible: false` with a reason such as `missing_maxi_brand`, `missing_competitor_brand`, `missing_maxi_size`, `missing_competitor_size`, or `identical_product_not_proven`.

## Price-Match Output

Each evaluated item should include:

- requested item
- Maxi product
- competitor product or offer
- eligibility status
- reasons for ineligibility, if any
- matched unit price
- quantity matched
- quantity not matched
- estimated savings
- flyer or source metadata
- current snapshot date

## Quantity Limit

The maximum price-match quantity is 4 units per same item.

If requested quantity exceeds 4, only 4 units may receive the matched price. Remaining units use the normal Maxi price.

## Current Snapshot Validity

For the MVP, a competitor product is considered current only if it comes from the latest `updated::date` snapshot. Historical rows in `public.epiceries_products` must not be mixed into current price matching.
