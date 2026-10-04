# ADR-001: Keep Deterministic Business Logic in Python Tools

## Status

Proposed

## Context

Fit AI uses LLMs to help users optimize grocery shopping. The system handles prices, distances, budgets, store constraints, price matching, offer validity, and quantity limits.

These operations affect correctness, user trust, and later model evaluation.

## Decision

The LLM will act as an orchestrator and strategy decision-maker.

Deterministic business logic will be implemented in Python tools and services, including:

- distance calculations
- price calculations
- cart totals
- budget validation
- store limits
- price-match eligibility
- price-match quantity limits
- offer validity
- current flyer snapshot selection
- purchasable package quantity calculation

The internal `calculate_package_nutrition` service will convert current `epiceries_products` nutrition references and actual product sizes into nutrition-per-package coefficients. The canonical catalog is taxonomy/mapping metadata and does not override database nutrition. The optimizer behind `build_basket_options` will then select integer package counts. Both are deterministic Python logic and neither is an additional LLM-facing tool.

## Consequences

Benefits:

- repeatable results
- easier testing
- clearer MLflow evaluation
- safer model comparison
- reduced hallucination risk
- easier debugging
- deterministic package and price-match behavior across models

Tradeoffs:

- more upfront tool design
- the LLM needs structured tool outputs
- strategy quality depends on tool coverage

## Non-Goals

This decision does not select a specific LLM model.

This decision does not define database schema or migrations.
