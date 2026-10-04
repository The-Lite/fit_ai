# Grocery Tools Implementation Plan

## Status

The September 20, 2026 grocery revision supersedes the earlier nutrition-oriented
plan. Implementation is authorized by the user's detailed MVP request.
See [revision plan](mvp-grocery-revision.md) for the inspection and scope,
[architecture](../architecture/agent-architecture.md) for the implemented policies,
and [contracts](../architecture/tool-contracts.md) for request/result models.

## Implemented scope

- Reuse connection/settings, repositories, user context, Haversine distances,
  deterministic package parsing and amount-based quantity arithmetic.
- Add requirement planning with explicit and automatic modes and runtime dietary
  context. Centralize versioned food aliases, tags and goal strategies.
- Upgrade search to current-snapshot bilingual, fuzzy, relevance-filtered retrieval
  with bounded SQL candidates and deterministic Python ranking.
- Extend quantities with explicit package counts and one-package defaults.
- Implement strict Maxi identity checking, current-offer verification and capped
  deterministic price arithmetic.
- Implement exact basket alternatives over retrieved candidates with an explicit
  complexity limit, required/optional priorities and hard budget/store/distance
  constraints.
- Expose all six grocery tools, document their schemas, and add unit/integration
  validation. Record live retrieval examples and final checks in the revision report.

## Boundaries

No nutrition data/formulas, production data/schema mutations, PostgreSQL extension
installation, index creation, MLflow changes or conversational-agent implementation.
Detailed stored preferences/allergies require separate future schema approval;
the MVP accepts those as declared runtime inputs without requiring a migration.

Exact optimization was the recommended option in the implementation clarification;
with no preference received before dependent work, that documented default was used.
No solver library or infrastructure was added. Limits are operational safeguards,
not permission to return an approximation as an exact result.
