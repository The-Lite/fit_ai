# Phase 0 PostgreSQL Schema Verification

## Status

Verified read-only on 2026-09-13. Phases 1-4 may proceed against the current schema. Nutrition-dependent phases remain deferred.

## Method

The five approved `public` tables were inspected through PostgreSQL `information_schema.columns`. No tables, rows, constraints, or schemas were modified.

## Verified Tables

### `public.users`

| Column | PostgreSQL type | Nullable |
| --- | --- | --- |
| `user_id` | `integer` | no |
| `username` | `character varying` | no |
| `age` | `integer` | no |
| `weight_kg` | `numeric(6,2)` | no |
| `height_cm` | `numeric(6,2)` | no |
| `goal` | `character varying` | no |
| `vegetarian` | `integer` | no |
| `budget` | `numeric(10,2)` | no |
| `created_at` | `timestamp without time zone` | yes |

### `public.user_locations`

| Column | PostgreSQL type | Nullable |
| --- | --- | --- |
| `user_location_id` | `integer` | no |
| `user_id` | `integer` | no |
| `location_label` | `character varying` | no |
| `address` | `text` | no |
| `latitude` | `numeric(9,6)` | no |
| `longitude` | `numeric(9,6)` | no |

### `public.user_shopping_preferences`

| Column | PostgreSQL type | Nullable |
| --- | --- | --- |
| `user_id` | `integer` | no |
| `shopping_priority` | `character varying` | no |
| `max_stores` | `integer` | no |
| `max_distance_km` | `numeric(6,2)` | no |
| `minimum_savings_for_extra_store` | `numeric(10,2)` | no |

### `public.store_locations`

| Column | PostgreSQL type | Nullable |
| --- | --- | --- |
| `store_location_id` | `integer` | no |
| `store_brand` | `character varying` | no |
| `store_name` | `character varying` | no |
| `address` | `text` | no |
| `city` | `character varying` | no |
| `postal_code` | `character varying` | yes |
| `latitude` | `numeric(9,6)` | no |
| `longitude` | `numeric(9,6)` | no |

### `public.epiceries_products`

| Column | PostgreSQL type | Nullable |
| --- | --- | --- |
| `id` | `character varying` | no |
| `name` | `text` | no |
| `brand` | `text` | yes |
| `size` | `text` | yes |
| `unit_price` | `jsonb` | yes |
| `image` | `text` | yes |
| `category_id` | `integer` | yes |
| `price` | `double precision` | yes |
| `store` | `character varying` | yes |
| `discounted` | `boolean` | yes |
| `prices` | `jsonb` | yes |
| `link` | `text` | yes |
| `url` | `text` | yes |
| `category_name` | `text` | yes |
| `updated` | `timestamp with time zone` | yes |
| `loaded_at` | `timestamp with time zone` | no |

## Deferred Nutrition Extension

The verified `public.epiceries_products` schema contains none of the required nutrition concepts:

- serving/reference amount or unit
- calories
- protein
- carbohydrates
- sugars
- fiber
- fat
- saturated fat
- sodium

The existing `size` column describes product package size; it cannot establish the nutrition reference basis by itself. `unit_price` and `prices` are pricing JSON fields and must not be treated as nutrition data.

Consequently, the current repository maps only verified product fields, and no nutrition-per-package calculation is implemented. This does not block user context, distances, current-product retrieval, package parsing, or amount-based purchase-quantity calculation.

## Required Resolution

Before nutrition planning and optimization proceed, one of the following must occur:

1. Add and populate nutrition columns in `public.epiceries_products`, then rerun this read-only verification.
2. Provide the intended database/schema if the inspected local `fit_ai` database is not the target containing nutrition data.

Creating or applying a schema migration is outside the current authorization and requires separate explicit approval. Future nutrition columns will be added through the `ProductRepository` row mapping and product domain boundary; current code must not guess their names, types, units, or nullability.
