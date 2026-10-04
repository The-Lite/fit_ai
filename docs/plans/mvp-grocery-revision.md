# Grocery MVP revision

Authorized by the September 20, 2026 implementation request. This supersedes
nutrition-dependent portions of the original implementation plan.

## Findings

Reuse the database connection, verified row mapping, user context, distances,
package parser and Decimal quantity calculations. Planning, price matching and
basket optimization were documented but unimplemented. Detailed preferences and
allergies are not stored columns; accept declared runtime context explicitly.

Read-only inspection: 68,330 products; latest `updated::date` is 2026-08-29;
only `plpgsql` is installed. Product and location stores agree on `iga`, `maxi`,
`metro`, `provigo`, `superc`, `walmart`. No extension or schema change is needed.

## Implementation

- Centralize versioned EN/FR concepts, tags, exclusions and ordered goal strategies.
- Normalize explicit requirements; generate optional defaults only for an empty list.
- Resolve aliases and conservative spelling errors; retrieve bounded SQL candidates
  from one repository-selected snapshot; filter and rank without price signals.
- Extend existing quantity arithmetic with explicit package counts and a one-package
  default; never infer unknown physical sizes.
- Prove Maxi equivalence using normalized name, brand and parsed size, independently
  of food-search scores; cap discounted packages at four per identical item.
- Build deterministic alternatives under budget, store, distance and extra-store
  savings constraints; disclose unsatisfied required foods and excluded defaults.
- Keep exactly six public tools; update contracts, architecture and relevant tests.

Affected areas: `config/food_catalog.py`, planning/price-matching/basket domain and
service modules, existing product repository/search/quantity modules, grocery tool
adapters, tests, architecture/product/decision documentation. User and distance
implementations remain reusable without changes. No production writes, migrations,
MLflow changes, nutrition formulas or agent orchestration are included.

Validation: unit tests, read-only PostgreSQL integration checks and retrieval
examples, then Pytest and Ruff. Exact versus bounded optimization is being clarified
with the developer before optimizer implementation.
