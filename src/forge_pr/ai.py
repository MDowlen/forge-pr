from __future__ import annotations

import json
import os
import urllib.error
import urllib.request
from typing import TypeVar

from pydantic import BaseModel

from .models import AgentReviewOutput, AgentTestOutput

T = TypeVar("T", bound=BaseModel)


def _output_text(body: dict) -> str:
    for item in body.get("output", []):
        if item.get("type") != "message":
            continue
        for content in item.get("content", []):
            if content.get("type") == "output_text":
                return str(content.get("text", ""))
    raise RuntimeError("Model response did not contain output_text")


class OpenAIReviewClient:
    """Responses API client using JSON-schema structured outputs."""

    def __init__(
        self,
        api_key: str | None = None,
        model: str | None = None,
        base_url: str = "https://api.openai.com/v1",
    ) -> None:
        self.api_key = api_key or os.getenv("OPENAI_API_KEY")
        self.model = model or os.getenv("FORGE_PR_MODEL", "gpt-5.4-mini")
        self.base_url = base_url.rstrip("/")

    @property
    def enabled(self) -> bool:
        return bool(self.api_key)

    def _structured(self, *, instructions: str, input_text: str, schema: type[T]) -> T:
        if not self.api_key:
            raise RuntimeError("OPENAI_API_KEY is not configured")
        payload = {
            "model": self.model,
            "instructions": instructions,
            "input": input_text,
            "store": False,
            "text": {
                "format": {
                    "type": "json_schema",
                    "name": schema.__name__.lower(),
                    "schema": schema.model_json_schema(),
                    "strict": False,
                }
            },
        }
        request = urllib.request.Request(
            f"{self.base_url}/responses",
            data=json.dumps(payload).encode("utf-8"),
            headers={
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
            },
            method="POST",
        )
        try:
            with urllib.request.urlopen(request, timeout=90) as response:
                body = json.loads(response.read().decode("utf-8"))
        except urllib.error.HTTPError as exc:
            detail = exc.read().decode("utf-8", errors="replace")
            raise RuntimeError(f"OpenAI review request failed ({exc.code}): {detail}") from exc
        except urllib.error.URLError as exc:
            raise RuntimeError(f"OpenAI review request failed: {exc.reason}") from exc
        return schema.model_validate_json(_output_text(body))

    def review(self, payload: dict) -> AgentReviewOutput:
        instructions = (
            "You are ForgePR's quality and safety reviewer. Review only the supplied PR diff and "
            "grounded repository context. Do not invent files, behavior, or citations. Findings must "
            "be actionable. Use high/critical severity only for material correctness, security, data "
            "loss, or architectural regression risk."
        )
        return self._structured(
            instructions=instructions,
            input_text=json.dumps(payload, sort_keys=True),
            schema=AgentReviewOutput,
        )

    def generate_tests(self, payload: dict) -> AgentTestOutput:
        instructions = (
            "You are ForgePR's test-generation agent. Propose focused regression coverage for changed "
            "behavior using only supplied diff/context. Generate pytest test files only when Python "
            "behavior is sufficiently grounded; otherwise return suggestions without invented code."
        )
        return self._structured(
            instructions=instructions,
            input_text=json.dumps(payload, sort_keys=True),
            schema=AgentTestOutput,
        )
