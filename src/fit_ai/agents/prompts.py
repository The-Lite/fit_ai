"""Versioned prompt registry for the Fit AI grocery agent.

Prompts are stored as named, versioned strings so MLflow can log the exact
prompt text used in each experiment run. The registry is a plain dict — no
external service, no files to sync. Add a new version by appending a new key.

Prompt naming convention: ``<role>/<purpose>__v<n>``

The router uses JEV (a decision model) so it does not use a text prompt.
The answer model (a language model) uses the prompts here.
"""

from __future__ import annotations

PROMPT_REGISTRY: dict[str, str] = {
    # ── Answer model: turns verified tool results into a user-facing reply ──
    "answer_model/system__v1": (
        "You are Fit AI, a grocery shopping assistant for Montreal-area users.\n"
        "You help users plan weekly grocery baskets within budget and store constraints.\n\n"
        "## What you do\n"
        "You receive the output of deterministic grocery tools:\n"
        "- user context (profile, location, budget, shopping preferences)\n"
        "- a food plan (required and optional foods with quantities)\n"
        "- product search results (real products from local stores)\n"
        "- store distances (Haversine km from the user)\n"
        "- basket options (optimized combinations with totals, savings, coverage)\n\n"
        "## Rules\n"
        "1. NEVER recalculate prices, quantities, totals, or savings. The tools are authoritative.\n"
        "2. Present each basket option clearly: which foods are covered, which stores, the total, and whether it fits the budget.\n"
        "3. If some foods are unfulfilled, say so explicitly. Do not claim completeness if the data says incomplete.\n"
        "4. Do not invent nutrition claims. These are grocery suggestions, not nutritional prescriptions.\n"
        "5. Mention distance and store count tradeoffs when comparing options.\n"
        "6. If price-match savings apply, mention them but do not recompute the amounts.\n"
        "7. Be concise. Use bullet points for items. Show totals in CAD.\n"
        "8. If the user asked for specific foods, confirm they were included.\n"
        "9. If foods were auto-generated from a goal, say which goal strategy was used.\n"
        "10. Respond in the same language as the user's request (English or French).\n"
    ),
    "answer_model/user_template__v1": (
        "## User request\n"
        "{user_request}\n\n"
        "## User context\n"
        "- Name: {username}\n"
        "- Goal: {goal}\n"
        "- Budget: ${budget}\n"
        "- Shopping priority: {shopping_priority}\n"
        "- Max stores: {max_stores}\n"
        "- Max distance: {max_distance_km} km\n\n"
        "## Basket options\n"
        "{basket_json}\n\n"
        "## Food plan warnings\n"
        "{warnings}\n\n"
        "Write a clear, helpful reply to the user. Present the best option first, "
        "then mention alternatives. Highlight any unfulfilled foods and explain why.\n"
    ),
    # ── JEV routing questions — stored for traceability, not sent as text ──
    "jev/router_state_template__v1": (
        "User request: {user_request}\n"
        "User goal: {goal}\n"
        "User budget: {budget}\n"
        "Vegetarian: {vegetarian}\n"
    ),
}

PROMPT_VERSIONS: dict[str, str] = {
    "answer_model/system": "v1",
    "answer_model/user_template": "v1",
    "jev/router_state_template": "v1",
}


def get_prompt(name: str) -> str:
    """Get a prompt by its registry name (e.g. 'answer_model/system__v1')."""
    if name not in PROMPT_REGISTRY:
        raise KeyError(f"Prompt '{name}' not found in registry")
    return PROMPT_REGISTRY[name]


def get_prompt_versioned(role: str) -> str:
    """Get the current versioned prompt name for a role (e.g. 'answer_model/system')."""
    version = PROMPT_VERSIONS.get(role)
    if version is None:
        raise KeyError(f"No version registered for prompt role '{role}'")
    return f"{role}__{version}"
