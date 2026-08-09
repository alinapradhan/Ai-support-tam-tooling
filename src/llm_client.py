"""
Thin wrapper around the Anthropic API.

Design choices (see DESIGN.md for the full write-up):
- Single call site for all LLM calls -> easy to add retries/logging/PII scrubbing in one place.
- temperature=0 everywhere by default, since Task 2 requires deterministic output and
  Task 1 benefits from stable classification.
- MOCK_MODE lets the eval harness / CI / reviewers without an API key still exercise
  the full pipeline deterministically using rule-based stand-ins. This keeps the repo
  runnable per the "must run from a clean install" requirement even without secrets.
"""

from __future__ import annotations

import json
import os
import re
from typing import Any

from dotenv import load_dotenv

load_dotenv()

MODEL = os.getenv("ANTHROPIC_MODEL", "claude-sonnet-4-6")
MOCK_MODE = os.getenv("MOCK_MODE", "0") == "1" or not os.getenv("ANTHROPIC_API_KEY")

_client = None


def _get_client():
    global _client
    if _client is None:
        import anthropic
        _client = anthropic.Anthropic()
    return _client


def _strip_json_fences(text: str) -> str:
    text = text.strip()
    text = re.sub(r"^```(json)?", "", text).strip()
    text = re.sub(r"```$", "", text).strip()
    return text


def call_llm_json(
    system_prompt: str,
    user_prompt: str,
    max_tokens: int = 1500,
    temperature: float = 0.0,
) -> dict[str, Any]:
    """
    Calls the model and parses a strict-JSON response.
    Raises ValueError if the model does not return parseable JSON (caller decides
    whether to retry, fall back, or flag needs_human_review).
    """
    if MOCK_MODE:
        raise RuntimeError(
            "call_llm_json invoked while MOCK_MODE is on. "
            "Callers should check llm_client.MOCK_MODE and use their rule-based fallback."
        )

    client = _get_client()
    response = client.messages.create(
        model=MODEL,
        max_tokens=max_tokens,
        temperature=temperature,
        system=system_prompt,
        messages=[{"role": "user", "content": user_prompt}],
    )
    raw_text = "".join(
        block.text for block in response.content if getattr(block, "type", None) == "text"
    )
    cleaned = _strip_json_fences(raw_text)
    try:
        return json.loads(cleaned)
    except json.JSONDecodeError as e:
        raise ValueError(f"Model did not return valid JSON: {e}\nRaw output:\n{raw_text}")
