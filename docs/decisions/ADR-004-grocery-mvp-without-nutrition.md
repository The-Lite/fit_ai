# ADR-004: Grocery MVP without nutrition optimization

## Status

Accepted by the September 20, 2026 user revision request. Supersedes the
nutrition-dependent portions of ADR-002, ADR-003 and the former tool contracts.

## Decision

The MVP plans food requirements rather than nutritional targets. User foods are
required; automatic goal candidates are optional. Explicit quantities remain
intact; absent quantities mean one purchasable package, not a body-weight formula.
Centralized EN/FR concepts, aliases, tags and default strategies are reference data.

The repository determines the latest product snapshot. Search uses bounded SQL
candidate retrieval and deterministic Python relevance. Only plpgsql was installed
when inspected; no extension or index is added. Fuzzy aliases never prove price
match equivalence. Maxi identity checks remain strict and quantities are capped
at four discounted packages per identical item.

Python computes requirements normalization, relevance, package counts, prices,
price-match savings, distances and basket choices. Exact dynamic programming
works over the retrieved candidates and stops explicitly at a configured
complexity limit. The LLM extracts the request, calls six tools and explains their
results. No nutrition completeness claim is allowed.

## Consequences

No database migration or nutrition enrichment is needed to ship this tool MVP.
Search vocabulary and metadata are finite; bounded candidates can omit products.
Package counts do not guarantee a week's food sufficiency. Catalog restriction
filtering cannot verify full ingredients or cross-contact. Missing data and
unsatisfied required foods remain explicit. Future nutrition work needs separate
requirements and verified data; this revision adds no speculative fields.
