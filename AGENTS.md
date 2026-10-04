# Fit AI — Codex Instructions

## Project

Fit AI is an AI-powered grocery optimization project built with Python.

The project uses:
- PostgreSQL for application data
- MLflow for experiments and evaluation
- Vercel AI Gateway for access to different LLMs
- Python for deterministic business logic and agent tools

## Development Style

This project uses supervised AI-assisted development.

The human developer remains responsible for architectural and implementation decisions.

Codex should act as a software engineering partner, not as an autonomous developer.

## Workflow

For significant features or architectural changes:

1. Inspect the existing repository and relevant documentation.
2. Explain the current situation.
3. Propose an approach.
4. Identify files that would need to change.
5. Wait for explicit approval before implementation.

Do not automatically move from planning to implementation.

## Implementation Rules

When implementation is explicitly approved:

- Modify only files required for the approved task.
- Keep changes small and focused.
- Prefer modular and testable Python.
- Use type hints.
- Prefer absolute imports from `fit_ai`.
- Do not duplicate existing business logic.
- Do not refactor unrelated code.

After completing the approved implementation, stop and report what changed.

## Testing

Do not automatically fix failing tests unless explicitly instructed.

When asked to run tests:

1. Run the requested tests.
2. Report failures clearly.
3. Explain the likely cause.
4. Wait for approval before modifying code to fix them.

## Database Safety

PostgreSQL contains project data.

Do not without explicit approval:

- DROP tables or databases
- TRUNCATE tables
- DELETE data
- modify database schemas
- create or apply migrations
- reset existing data

Read-only inspection is allowed when needed for an approved task.

## MLflow Safety

Do not without explicit approval:

- delete experiments
- delete runs
- reset MLflow data
- start or reconfigure MLflow infrastructure

## Secrets

Never:

- expose `.env` contents
- print API keys
- commit credentials
- hard-code secrets

Use environment variables for credentials.

## Agent Architecture Principle

Fit AI's application LLM should primarily perform orchestration and decision-making.

Deterministic operations should normally remain in Python.

Examples include:

- price calculations
- distance calculations
- cart totals
- budget validation
- price-match eligibility
- quantity limits
- offer validity

Do not move deterministic business rules into LLM prompts without discussing the architectural reason first.

## Documentation

Use:

- `docs/product/` for product requirements and behavior
- `docs/architecture/` for technical architecture
- `docs/decisions/` for important architectural decisions
- `docs/plans/` for implementation plans

When asked to design a significant feature, prefer documenting the agreed design before implementing it.

## Important

If requirements are ambiguous or an architectural decision has multiple reasonable approaches, present the alternatives and ask for a decision instead of silently choosing one.

Do not continue into additional development tasks without explicit instruction.