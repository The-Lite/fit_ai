"""Deterministic food identity and relevance policy shared across layers."""

from __future__ import annotations

import re
import unicodedata
from difflib import SequenceMatcher

from fit_ai.config.food_catalog import (
    CONCEPT_EXCLUSIONS,
    FOOD_CONCEPTS,
    PREPARED_CONTEXTS,
)
from fit_ai.domain.products import Product


def normalize(text: str) -> str:
    text = text.casefold().replace("œ", "oe").replace("æ", "ae")
    text = "".join(
        char
        for char in unicodedata.normalize("NFKD", text)
        if not unicodedata.combining(char)
    )
    return " ".join(re.findall(r"[^\W_]+", text, re.UNICODE))


def contains(text: str, phrase: str) -> bool:
    return f" {phrase} " in f" {text} "


def resolve_concept(query: str) -> str | None:
    query = normalize(query)
    exact = [
        key
        for key, value in FOOD_CONCEPTS.items()
        if query in {normalize(alias) for alias in value.aliases} | {normalize(key)}
    ]
    if exact:
        return min(exact, key=lambda key: (len(FOOD_CONCEPTS[key].aliases), key))
    if len(query) < 4:
        return None
    # Resolve each shared alias to its most specific concept before comparing
    # scores. "saumon" in both fish and salmon is one spelling, not ambiguity.
    aliases = {
        normalize(alias)
        for concept in FOOD_CONCEPTS.values()
        for alias in concept.aliases
    }
    scores: dict[str, float] = {}
    for alias in aliases:
        owners = [
            key
            for key, concept in FOOD_CONCEPTS.items()
            if alias in {normalize(a) for a in concept.aliases}
        ]
        owner = min(owners, key=lambda key: (len(FOOD_CONCEPTS[key].aliases), key))
        scores[owner] = max(
            scores.get(owner, 0.0), SequenceMatcher(None, query, alias).ratio()
        )
    ranked = sorted(scores.items(), key=lambda pair: (-pair[1], pair[0]))
    key, best = ranked[0]
    if best >= 0.82 and best - ranked[1][1] >= 0.04:
        return key
    return None


def query_aliases(query: str) -> tuple[str | None, tuple[str, ...]]:
    concept = resolve_concept(query)
    aliases = FOOD_CONCEPTS[concept].aliases if concept else (query,)
    return concept, tuple(
        sorted({normalize(alias) for alias in aliases if normalize(alias)})
    )


def rank_product(query: str, product: Product) -> tuple[float, str]:
    concept, aliases = query_aliases(query)
    name = normalize(product.name)
    category = normalize(product.category_name or "")
    if not aliases:
        return 0.0, "empty_query"
    if concept and any(
        contains(name + " " + category, normalize(p)) for p in PREPARED_CONTEXTS
    ):
        return 0.0, "prepared_or_flavoured_product"
    if concept and any(
        contains(name, normalize(p)) for p in CONCEPT_EXCLUSIONS.get(concept, ())
    ):
        return 0.0, "different_food_context"
    score, reason = 0.0, "insufficient_relevance"
    for alias in aliases:
        if name == alias:
            candidate, why = 1.0, "exact_alias"
        elif contains(name, alias):
            candidate, why = 0.94, "bilingual_whole_phrase"
        elif set(alias.split()) <= set(name.split()):
            candidate, why = 0.88, "bilingual_token_match"
        else:
            length = len(alias.split())
            words = name.split()
            fuzzy = max(
                (
                    SequenceMatcher(
                        None, alias, " ".join(words[i : i + length])
                    ).ratio()
                    for i in range(max(0, len(words) - length + 1))
                ),
                default=0.0,
            )
            candidate, why = (
                (round(fuzzy * 0.9, 6), "fuzzy_name")
                if fuzzy >= 0.86
                else (0.0, reason)
            )
        if candidate and contains(category, alias):
            candidate = min(1.0, candidate + 0.02)
            why += "_category"
        if candidate > score:
            score, reason = candidate, why
    return score, reason
