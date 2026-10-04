# Grocery Agent MVP

Fit AI helps users buy relevant real groceries within budget, store and distance
constraints. Nutrition optimization is outside this MVP. Recommendations must
never claim exact calorie, protein or other nutritional coverage.

## Two supported flows

1. Explicit foods: preserve the user's requested foods and quantities as required
   requirements. Search both English and French products without asking the user
   for database product names. Do not substitute an automatic grocery list.
2. No food choices: generate optional candidates using the user's goal and declared
   preferences/restrictions. Muscle gain, maintenance and weight loss use centrally
   configured strategies; these are ordinary food ideas, not nutritional formulas.

Allergies/restrictions override defaults. Explicit conflicts remain visible and
blocked. The database currently provides a vegetarian flag, weight, goal, budget,
location and shopping preferences. Other dietary context is supplied at runtime
and is not claimed to be stored. Weight does not determine food amounts.

## Purchasing behavior

Use only products from the repository-selected latest updated-date snapshot.
Resolve known bilingual aliases and misspellings; return ranked candidates or an
explicit unmatched result. Reject irrelevant prepared/flavoured products before
optimizing price. Search similarity is independent of strict Maxi equivalence.

Explicit physical amounts use deterministic ceiling package arithmetic. Explicit
bag/package requests preserve package count. Without quantities, buy one package
per selected food. Ambiguous sizes never acquire an invented physical amount.

Maxi price matching follows the documented competitor, identity, snapshot and
four-package rules. The optimizer enforces hard budget, max stores and distance,
prioritizes required foods, and includes optional foods where feasible. It may
return lower-cost, fewer-store and nearer alternatives. Extra-store savings
compare equivalent food coverage; necessary extra visits are disclosed.

## Output

Each option gives actual products, quantities, stores, locations, total, savings,
distance summary, budget compliance and separately reported unfulfilled required
foods and excluded defaults. A partial request is never described as complete.
Oversized exact searches return an explicit complexity-limit reason.

The public tool list and executable schemas are documented in
`../architecture/tool-contracts.md`. No conversational agent, model gateway,
MLflow infrastructure, nutrition enrichment or production migrations are included.
