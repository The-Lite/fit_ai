"""End-to-end test for the grocery agent with MLflow tracing.

Requires:
- PostgreSQL running with the fit_ai database populated
- MLflow server running at http://127.0.0.1:5000 (or MLFLOW_TRACKING_URI set)
- Vercel AI Gateway API key in .env (api_key)
- JEV model accessible via the gateway

Run:
    ./.venv/bin/python -m pytest tests/integration/test_grocery_agent.py -v
"""

import os

import mlflow
import pytest

from fit_ai.agents import GroceryAgent


@pytest.fixture
def mlflow_tracking():
    """Ensure MLflow is connected and the experiment exists."""
    uri = os.environ.get("MLFLOW_TRACKING_URI", "http://127.0.0.1:5000")
    mlflow.set_tracking_uri(uri)
    mlflow.set_experiment("fit_ai_grocery_agent")


@pytest.mark.integration
def test_grocery_agent_weekly_basket(mlflow_tracking):
    """The agent handles a 'weekly basket for muscle gain' request end-to-end."""
    agent = GroceryAgent()
    state = agent.run("Make me a weekly basket for muscle gain", user_id=1)

    # JEV classified intent correctly
    assert state.jev_decisions["intent"].value == "weekly_basket"
    assert state.jev_decisions["needs_food_planning"].value >= 0.5

    # Deterministic tools produced results
    assert state.user_context is not None
    assert state.user_context["user"]["username"] == "Alice"
    assert len(state.food_plan["foods"]) > 0
    assert state.food_plan["mode"] == "automatic"

    # Product search found matches
    matched = [
        g for g in state.search_result.get("product_matches", [])
        if g["status"] == "matched"
    ]
    assert len(matched) > 0

    # Store distances were computed
    assert len(state.store_distances.get("stores", [])) > 0

    # Basket options were built
    assert len(state.basket_result.get("options", [])) > 0
    for option in state.basket_result["options"]:
        assert option["within_budget"] is True

    # Answer model produced a response
    assert state.answer is not None
    assert len(state.answer) > 100

    # MLflow captured traces
    mlflow.flush_trace_async_logging()
    traces = mlflow.search_traces()
    assert len(traces) > 0, "No traces were logged"

    # The latest trace has the expected span structure
    trace = mlflow.get_trace(traces.iloc[0].trace_id)
    span_names = {span.name for span in trace.data.spans}
    assert "grocery_agent_run" in span_names
    assert "jev_classify_intent" in span_names
    assert "answer_model_generate" in span_names
