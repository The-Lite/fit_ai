from fit_ai.domain.food_matching import normalize

STORE_ALIASES = {
    "maxi": "maxi",
    "super c": "superc",
    "superc": "superc",
    "walmart": "walmart",
    "metro": "metro",
    "iga": "iga",
    "provigo": "provigo",
}
PRICE_MATCH_COMPETITORS = frozenset({"superc", "walmart", "metro", "iga", "provigo"})


def store_identity(value: str | None) -> str:
    normalized = normalize(value or "")
    return STORE_ALIASES.get(normalized, normalized)
