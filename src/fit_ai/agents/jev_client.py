"""JEV decision model client for the Vercel AI Gateway evaluate API.

JEV (typesafe-ai/jev) is a probabilistic decision model, not a chat model.
It evaluates state against typed questions (choice, score, boolean) and
returns typed answers with probabilities — no prose generation.

This client wraps the HTTP API at https://ai-gateway.vercel.sh/v1/evaluate
so the rest of the agent talks Python, not raw HTTP.
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Any

import requests
from dotenv import load_dotenv

load_dotenv()

GATEWAY_BASE = "https://ai-gateway.vercel.sh/v1"
JEV_MODEL = "typesafe-ai/jev"


@dataclass(frozen=True)
class JevAnswer:
    """A single typed answer from JEV."""

    question_id: str
    answer_type: str  # "choice" | "score" | "boolean"
    value: Any  # str for choice, float for score, float (probability) for boolean
    probabilities: dict[str, float]
    confidence: float | None = None


class JevClient:
    """Thin client around the JEV evaluate endpoint."""

    def __init__(
        self,
        api_key: str | None = None,
        base_url: str = GATEWAY_BASE,
        model: str = JEV_MODEL,
    ) -> None:
        self._api_key = api_key or os.environ["api_key"]
        self._base_url = base_url
        self._model = model

    def evaluate(
        self,
        state: str | dict[str, Any],
        questions: dict[str, dict[str, Any]],
    ) -> dict[str, JevAnswer]:
        """Evaluate state against typed questions.

        Args:
            state: The context for JEV to evaluate — a string or JSON object.
            questions: A map of question IDs to question specs.
                Each spec has:
                  - "type": "choice" | "score" | "boolean"
                  - "instructions": str
                  - "criteria": depends on type
                    (choice: dict of option→description,
                     score: list of level descriptions low→high,
                     boolean: optional {"true": ..., "false": ...})

        Returns:
            A dict mapping question IDs to JevAnswer objects.
        """
        payload = {
            "model": self._model,
            "state": state,
            "questions": questions,
        }
        response = requests.post(
            f"{self._base_url}/evaluate",
            headers={
                "Authorization": f"Bearer {self._api_key}",
                "Content-Type": "application/json",
            },
            json=payload,
            timeout=60,
        )
        response.raise_for_status()
        data = response.json()
        answers: dict[str, JevAnswer] = {}
        for qid, raw in data.get("answers", {}).items():
            atype = raw["type"]
            if atype == "choice":
                value = raw.get("choice")
            elif atype == "score":
                value = raw.get("score")
            else:  # boolean
                value = raw.get("probability")
            provider_meta = data.get("providerMetadata", {})
            typesafe_conf = provider_meta.get("typesafe", {}).get("confidence", {})
            answers[qid] = JevAnswer(
                question_id=qid,
                answer_type=atype,
                value=value,
                probabilities=raw.get("probabilities", {}),
                confidence=typesafe_conf.get(qid),
            )
        return answers
