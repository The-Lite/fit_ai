"""Grocery agent: JEV routes, Python tools compute, a language model answers.

Architecture (from the previous session's recommendation):

    User request
      → JEV interprets intent (decision model: choice + boolean questions)
      → get_user_context        (deterministic, from PostgreSQL)
      → plan_weekly_food_basket (deterministic, from the food catalog)
      → search_current_products (deterministic, bilingual product search)
      → get_store_distances      (deterministic, Haversine)
      → build_basket_options     (deterministic, exact DP optimization)
      → answer model             (language model, explains verified results)
      → user

JEV (typesafe-ai/jev) is a probabilistic decision model — it does not generate
prose. It evaluates state against typed questions and returns choices, scores,
and boolean probabilities. The agent uses it to:

  1. Classify the user's intent (weekly basket vs. explicit foods vs. other)
  2. Decide whether the agent should generate food candidates from the user's goal

All deterministic logic (prices, quantities, budget, distances, basket
optimization) stays in Python. JEV only interprets intent. The answer model
only explains verified results — it never recalculates.

MLflow tracing instruments every step so each run is visible in the MLflow UI.
"""

from __future__ import annotations

import json
import os
from dataclasses import dataclass, field
from decimal import Decimal
from typing import Any

import mlflow
from dotenv import load_dotenv
from mlflow.entities import SpanType
from openai import OpenAI

from fit_ai.agents.jev_client import JevAnswer, JevClient
from fit_ai.agents.prompts import get_prompt, get_prompt_versioned
from fit_ai.config.food_catalog import GOAL_STRATEGIES
from fit_ai.domain.baskets import BasketResult
from fit_ai.domain.planning import FoodInput, FoodPlanRequest, PlanningContext
from fit_ai.domain.products import FoodQuery, ProductSearchRequest
from fit_ai.domain.users import UserContext
from fit_ai.tools.grocery import (
    Coordinates,
    StoreDistanceRequest,
    build_basket_options,
    get_store_distances,
    get_user_context,
    plan_weekly_food_basket,
    search_current_products,
)

load_dotenv()

MLFLOW_TRACKING_URI = os.environ.get(
    "MLFLOW_TRACKING_URI", "http://127.0.0.1:5000"
)
EXPERIMENT_NAME = "fit_ai_grocery_agent"
ANSWER_MODEL = os.environ.get("FIT_AI_ANSWER_MODEL", "openai/gpt-4.1-mini")
MLFLOW_ENABLED = False


def _ensure_mlflow() -> None:
    """Configure MLflow tracking and tracing once on import."""
    global MLFLOW_ENABLED
    if MLFLOW_ENABLED:
        return
    mlflow.set_tracking_uri(MLFLOW_TRACKING_URI)
    mlflow.set_experiment(EXPERIMENT_NAME)
    # Enable OpenAI SDK autolog so answer-model calls are traced automatically.
    try:
        mlflow.openai.autolog()
    except Exception:
        pass
    MLFLOW_ENABLED = True


_ensure_mlflow()


@dataclass
class AgentState:
    """Mutable state carried through the agent pipeline."""

    user_request: str
    user_id: int
    user_context: dict[str, Any] | None = None
    food_plan: dict[str, Any] | None = None
    search_result: dict[str, Any] | None = None
    store_distances: dict[str, Any] | None = None
    basket_result: dict[str, Any] | None = None
    jev_decisions: dict[str, JevAnswer] = field(default_factory=dict)
    answer: str | None = None
    answer_model_usage: dict[str, Any] | None = None


class GroceryAgent:
    """Orchestrates JEV routing + deterministic tools + an answer model."""

    def __init__(
        self,
        jev_client: JevClient | None = None,
        answer_client: OpenAI | None = None,
        answer_model: str = ANSWER_MODEL,
    ) -> None:
        self._jev = jev_client or JevClient()
        api_key = os.environ.get("api_key", "")
        self._answer_client = answer_client or OpenAI(
            api_key=api_key,
            base_url="https://ai-gateway.vercel.sh/v1",
        )
        self._answer_model = answer_model

    # ── JEV intent classification ──────────────────────────────────────────

    @mlflow.trace(span_type=SpanType.AGENT, name="jev_classify_intent")
    def _classify_intent(self, user_request: str, user_ctx: dict[str, Any]) -> dict[str, JevAnswer]:
        """Use JEV to classify the user's intent and decide on food planning."""
        user = user_ctx.get("user", {})
        state = {
            "user_request": user_request,
            "user_goal": user.get("goal", ""),
            "user_budget": str(user.get("budget", "")),
            "vegetarian": user.get("vegetarian", False),
        }
        questions = {
            "intent": {
                "type": "choice",
                "instructions": "What does the user want the grocery agent to do?",
                "criteria": {
                    "weekly_basket": "User wants a full weekly grocery basket plan, possibly from a goal like muscle gain or maintenance",
                    "explicit_foods": "User listed specific foods or products to buy",
                    "price_check": "User wants to compare prices or check price matches",
                    "other": "Something else entirely",
                },
            },
            "needs_food_planning": {
                "type": "boolean",
                "instructions": "Should the agent generate food candidates from the user's goal, rather than requiring the user to name specific foods?",
                "criteria": {
                    "true": "The user describes a goal or vague request and expects the agent to choose foods",
                    "false": "The user already specified exact foods or products",
                },
            },
            "has_budget_override": {
                "type": "boolean",
                "instructions": "Does the user mention a specific budget in their request that differs from their profile?",
            },
        }
        answers = self._jev.evaluate(state, questions)
        span = mlflow.get_current_active_span()
        if span:
            span.set_outputs({"answers": {k: v.value for k, v in answers.items()}})
        return answers

    # ── Deterministic tool steps (each traced) ─────────────────────────────

    @mlflow.trace(span_type=SpanType.TOOL, name="tool_get_user_context")
    def _get_user_context(self, user_id: int) -> dict[str, Any]:
        return get_user_context(user_id)

    @mlflow.trace(span_type=SpanType.TOOL, name="tool_plan_weekly_food_basket")
    def _plan_food(
        self,
        user_ctx: dict[str, Any],
        foods: tuple[FoodInput, ...],
        budget: Decimal | None,
        planning_context: PlanningContext,
    ) -> dict[str, Any]:
        # The tool output strips user_id from location/shopping_preferences.
        # FoodPlanRequest.accept_user_tool_payload re-injects it, but only
        # when the dict has a "user" key — which it does here.
        request = FoodPlanRequest(
            user_context=user_ctx,
            foods=foods,
            budget=budget,
            planning_context=planning_context,
        )
        return plan_weekly_food_basket(request)

    @mlflow.trace(span_type=SpanType.TOOL, name="tool_search_current_products")
    def _search_products(self, food_plan: dict[str, Any]) -> dict[str, Any]:
        food_queries = tuple(
            FoodQuery(food_id=food["food_id"], name=food["food_name"])
            for food in food_plan["foods"]
            if not food.get("restriction_reasons")
        )
        if not food_queries:
            return {
                "current_snapshot_date": "",
                "product_matches": [],
                "unmatched_foods": [f["food_id"] for f in food_plan["foods"]],
                "warnings": ["no_searchable_foods_after_restriction_filtering"],
            }
        request = ProductSearchRequest(food_queries=food_queries)
        return search_current_products(request)

    @mlflow.trace(span_type=SpanType.TOOL, name="tool_get_store_distances")
    def _get_store_distances(self, user_ctx: dict[str, Any]) -> dict[str, Any]:
        location = user_ctx["location"]
        request = StoreDistanceRequest(
            user_location=Coordinates(
                latitude=Decimal(location["latitude"]),
                longitude=Decimal(location["longitude"]),
            ),
        )
        return get_store_distances(request)

    @mlflow.trace(span_type=SpanType.TOOL, name="tool_build_basket_options")
    def _build_basket(
        self,
        food_plan: dict[str, Any],
        search_result: dict[str, Any],
        store_distances: dict[str, Any],
        user_ctx: dict[str, Any],
    ) -> dict[str, Any]:
        prefs = dict(user_ctx["shopping_preferences"])
        prefs["user_id"] = user_ctx["user"]["user_id"]
        from fit_ai.domain.baskets import BasketRequest
        request = BasketRequest(
            food_plan=food_plan,
            search_result=search_result,
            store_distances=store_distances,
            shopping_preferences=prefs,
        )
        return build_basket_options(request)

    # ── Answer model: turns verified results into prose ────────────────────

    @mlflow.trace(span_type=SpanType.LLM, name="answer_model_generate")
    def _generate_answer(self, state: AgentState) -> str:
        user = state.user_context["user"]
        prefs = state.user_context["shopping_preferences"]
        basket_json = json.dumps(state.basket_result, indent=2, default=str)
        warnings = "\n".join(
            state.food_plan.get("warnings", []) + state.basket_result.get("warnings", [])
        ) or "None"

        system_prompt = get_prompt(get_prompt_versioned("answer_model/system"))
        user_template = get_prompt(get_prompt_versioned("answer_model/user_template"))
        user_prompt = user_template.format(
            user_request=state.user_request,
            username=user["username"],
            goal=user["goal"],
            budget=user["budget"],
            shopping_priority=prefs.get("shopping_priority", "balanced"),
            max_stores=prefs.get("max_stores", 3),
            max_distance_km=prefs.get("max_distance_km", 50),
            basket_json=basket_json,
            warnings=warnings,
        )

        response = self._answer_client.chat.completions.create(
            model=self._answer_model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            max_tokens=1200,
            temperature=0.3,
        )
        state.answer_model_usage = {
            "prompt_tokens": response.usage.prompt_tokens,
            "completion_tokens": response.usage.completion_tokens,
            "total_tokens": response.usage.total_tokens,
        }
        return response.choices[0].message.content

    # ── Full pipeline ──────────────────────────────────────────────────────

    @mlflow.trace(span_type=SpanType.CHAIN, name="grocery_agent_run")
    def run(self, user_request: str, user_id: int) -> AgentState:
        """Run the full agent pipeline for a user request.

        Args:
            user_request: The user's natural-language request.
            user_id: The database user ID.

        Returns:
            AgentState with all intermediate results and the final answer.
        """
        state = AgentState(user_request=user_request, user_id=user_id)

        # 1. Load user context (deterministic)
        state.user_context = self._get_user_context(user_id)

        # 2. JEV classifies intent
        state.jev_decisions = self._classify_intent(
            user_request, state.user_context
        )

        # 3. Build food plan inputs based on JEV's decisions
        intent = state.jev_decisions.get("intent")
        needs_planning = state.jev_decisions.get("needs_food_planning")

        intent_value = intent.value if intent else "weekly_basket"
        should_plan = (
            needs_planning.value >= 0.5 if needs_planning else True
        )

        foods: tuple[FoodInput, ...] = ()
        budget: Decimal | None = None
        planning_context = PlanningContext()

        if intent_value == "weekly_basket" and should_plan:
            # Let the deterministic planner generate candidates from the user's goal.
            foods = ()
        elif intent_value == "explicit_foods":
            # JEV said the user listed foods — but parsing specific foods from
            # free text is not a JEV decision (JEV doesn't generate text).
            # For the MVP, we still let the planner handle it; a future step
            # can use a language model to extract foods.
            foods = ()
        # For "other" intents we still attempt a plan; the answer model can explain.

        # 4. Plan weekly food basket (deterministic)
        state.food_plan = self._plan_food(
            state.user_context, foods, budget, planning_context
        )

        # 5. Search current products (deterministic, bilingual)
        state.search_result = self._search_products(state.food_plan)

        # 6. Get store distances (deterministic)
        state.store_distances = self._get_store_distances(state.user_context)

        # 7. Build basket options (deterministic, exact DP)
        state.basket_result = self._build_basket(
            state.food_plan,
            state.search_result,
            state.store_distances,
            state.user_context,
        )

        # 8. Answer model explains the verified results
        state.answer = self._generate_answer(state)

        # Log the full state to MLflow
        mlflow.log_params({
            "user_id": user_id,
            "user_request": user_request[:200],
            "jev_intent": intent_value,
            "jev_needs_planning": should_plan,
            "answer_model": self._answer_model,
            "food_count": len(state.food_plan.get("foods", [])),
            "basket_option_count": len(state.basket_result.get("options", [])),
        })
        if state.answer_model_usage:
            mlflow.log_metrics({
                "answer_prompt_tokens": state.answer_model_usage["prompt_tokens"],
                "answer_completion_tokens": state.answer_model_usage["completion_tokens"],
                "answer_total_tokens": state.answer_model_usage["total_tokens"],
            })

        return state
