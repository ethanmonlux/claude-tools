from __future__ import annotations

import json
import logging
import re

import anthropic

from .config import settings

logger = logging.getLogger("claude_client")


class ClaudeDegradedError(Exception):
    """Claude was reachable but could not complete the request."""

    pass


class ClaudeOutputError(Exception):
    """Claude responded but the output could not be parsed."""

    pass


async def call_claude(
    *,
    system_prompt: str,
    user_prompt: str,
    anthropic_api_key: str,
    model: str,
    mock_json: str | None = None,
) -> str:
    """
    Call Claude with web search and return clean JSON string.

    Handles:
    - Client creation
    - web_search tool
    - Last text block extraction
    - Markdown fence stripping
    - Cite tag stripping
    - JSON extraction

    Raises:
        ClaudeDegradedError: API unavailable, billing error, or no API key.
        ClaudeOutputError: Claude responded but output could not be parsed.
    """
    if settings.claude_mode == "mock":
        if mock_json is None:
            raise ClaudeOutputError("claude_mode is mock but no mock_json provided")
        try:
            json.loads(mock_json)
        except json.JSONDecodeError as e:
            raise ClaudeOutputError(f"mock_json is not valid JSON: {e}") from e
        return mock_json

    if not anthropic_api_key:
        raise ClaudeDegradedError("ANTHROPIC_KEY not configured")

    try:
        client = anthropic.AsyncAnthropic(api_key=anthropic_api_key)
        message = await client.messages.create(
            model=model,
            max_tokens=4096,
            system=system_prompt,
            tools=[{"type": "web_search_20250305", "name": "web_search"}],
            messages=[{"role": "user", "content": user_prompt}],
        )
    except anthropic.APIStatusError as e:
        if e.status_code == 402:
            raise ClaudeDegradedError("API credit exhausted") from e
        raise ClaudeDegradedError(f"API error: {e.status_code}") from e
    except Exception as e:
        raise ClaudeDegradedError(f"API unavailable: {e}") from e

    # Extract last text block
    raw = None
    for block in reversed(message.content):
        if block.type == "text":
            raw = block.text
            break
    if raw is None:
        raise ClaudeOutputError("Claude response contained no text block")

    raw = raw.strip()

    # Strip markdown fences
    if raw.startswith("```"):
        raw = raw.split("\n", 1)[-1]
        raw = raw.rsplit("```", 1)[0].strip()

    # Strip <cite> tags injected by web search
    raw = re.sub(r"<cite[^>]*>", "", raw)
    raw = re.sub(r"</cite>", "", raw)

    # Extract JSON object
    start = raw.find("{")
    end = raw.rfind("}")
    if start != -1 and end != -1:
        raw = raw[start : end + 1]

    # Validate it parses
    try:
        json.loads(raw)
    except json.JSONDecodeError as e:
        raise ClaudeOutputError(f"Output is not valid JSON: {e}") from e

    return raw
