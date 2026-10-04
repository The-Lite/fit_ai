"""Versioned retrieval vocabulary and food choices, never nutrient prescriptions."""

from dataclasses import dataclass

CATALOG_VERSION = "mvp-1"
MIN_RELEVANCE = 0.75
CANDIDATE_LIMIT = 300


@dataclass(frozen=True)
class FoodConcept:
    name: str
    aliases: tuple[str, ...]
    category: str
    tags: frozenset[str] = frozenset()


def food(name: str, aliases: str, category: str, tags: str = "") -> FoodConcept:
    return FoodConcept(
        name, tuple(aliases.split("|")), category, frozenset(tags.split())
    )


FOOD_CONCEPTS = {
    "chicken": food("chicken", "chicken|poulet|poulets", "meat", "meat"),
    "chicken_breast": food(
        "chicken breast",
        "chicken breast|chicken breasts|poitrine de poulet|poitrines de poulet",
        "meat",
        "meat",
    ),
    "egg": food("eggs", "egg|eggs|oeuf|oeufs|œuf|œufs", "eggs", "egg animal"),
    "rice": food("rice", "rice|riz", "staples"),
    "potato": food(
        "potatoes", "potato|potatoes|pomme de terre|pommes de terre", "produce"
    ),
    "beef": food("beef", "beef|boeuf|bœuf", "meat", "meat"),
    "salmon": food("salmon", "salmon|saumon", "fish", "fish meat"),
    "tuna": food("tuna", "tuna|thon", "fish", "fish meat"),
    "fish": food(
        "fish",
        "fish|poisson|salmon|saumon|tuna|thon|tilapia|cod|morue",
        "fish",
        "fish meat",
    ),
    "milk": food("milk", "milk|lait", "dairy", "milk animal"),
    "yogurt": food("yogurt", "yogurt|yoghurt|yaourt|yogourt", "dairy", "milk animal"),
    "greek_yogurt": food(
        "Greek yogurt",
        "greek yogurt|greek yoghurt|yogourt grec|yaourt grec",
        "dairy",
        "milk animal",
    ),
    "oats": food("oats", "oats|oatmeal|avoine|flocons d'avoine", "staples", "gluten"),
    "pasta": food(
        "pasta", "pasta|pâtes|pates|spaghetti|macaroni", "staples", "wheat gluten"
    ),
    "bread": food("bread", "bread|pain", "staples", "wheat gluten"),
    "banana": food("bananas", "banana|bananas|banane|bananes", "produce"),
    "apple": food("apples", "apple|apples|pomme|pommes", "produce"),
    "broccoli": food("broccoli", "broccoli|brocoli|brocolis", "produce"),
    "spinach": food("spinach", "spinach|épinard|épinards|epinards", "produce"),
    "carrot": food("carrots", "carrot|carrots|carotte|carottes", "produce"),
    "lentil": food("lentils", "lentil|lentils|lentille|lentilles", "staples"),
    "tofu": food("tofu", "tofu|tofu ferme|firm tofu", "plant_protein", "soy"),
    "olive_oil": food("olive oil", "olive oil|huile d'olive", "pantry"),
}

GOAL_STRATEGIES = {
    "muscle_gain": (
        "chicken_breast",
        "egg",
        "greek_yogurt",
        "tuna",
        "fish",
        "tofu",
        "lentil",
        "rice",
        "oats",
        "potato",
        "banana",
        "broccoli",
        "spinach",
    ),
    "maintenance": (
        "egg",
        "chicken_breast",
        "lentil",
        "yogurt",
        "rice",
        "oats",
        "potato",
        "apple",
        "banana",
        "carrot",
        "broccoli",
    ),
    "weight_loss": (
        "chicken_breast",
        "egg",
        "tofu",
        "greek_yogurt",
        "lentil",
        "oats",
        "apple",
        "broccoli",
        "spinach",
        "carrot",
    ),
}

# Food words in these contexts do not identify the requested basic food.
PREPARED_CONTEXTS = (
    "soup",
    "soupe",
    "gravy",
    "sauce",
    "seasoning",
    "assaisonnement",
    "flavoured",
    "flavored",
    "saveur",
    "chips",
    "croustilles",
    "snack",
    "bouillon",
    "broth",
    "nuggets",
    "pizza",
    "dog",
    "cat",
    "chien",
    "chat",
    "pet food",
    "repas",
    "meal",
    "juice",
    "jus",
    "candy",
    "bonbon",
    "farci",
    "stuffed",
    "breaded",
    "pane",
    "chocolate",
    "chocolat",
    "pudding",
    "dessert",
    "cookie",
    "cookies",
    "biscuit",
    "biscuits",
    "crisps",
    "krispies",
)
CONCEPT_EXCLUSIONS = {
    "apple": ("pomme de terre", "pommes de terre", "potato"),
    "milk": ("coconut", "coco", "almond", "amande", "oat", "avoine", "soy", "soja"),
    "rice": ("rice cake", "rice cakes", "galettes de riz", "rice vinegar", "vinaigre"),
    "egg": ("egg roll", "egg rolls", "liquid", "liquide", "substitute"),
}
