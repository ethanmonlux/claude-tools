from __future__ import annotations

import json
from unittest.mock import AsyncMock, patch

from httpx import ASGITransport, AsyncClient

from app.config import settings
from app.connectors.mock import MockConnector
from app.main import app
from app.models import ResearchResponse
from app.skills import prospect_research


# ---------------------------------------------------------------------------
# Test 1: degraded response when no API key is provided
# ---------------------------------------------------------------------------


async def test_run_mock_no_api_key():
    connector = MockConnector()
    response = await prospect_research.run(
        company_name="TestCo",
        notes="",
        connector=connector,
        anthropic_api_key="",
        model="claude-haiku-4-5-20251001",
    )
    assert response.status == "degraded"
    assert response.data is None
    assert response.error is not None


# ---------------------------------------------------------------------------
# Test 2: connector error is caught gracefully
# ---------------------------------------------------------------------------


async def test_connector_error_handled():
    class BrokenConnector:
        async def search_company(self, company_name: str) -> dict:
            raise RuntimeError("boom")

        async def get_recent_news(self, company_name: str) -> list[str]:
            return []

        async def create_note(self, company_id: str, note_body: str) -> str:
            return ""

    response = await prospect_research.run(
        company_name="TestCo",
        notes="",
        connector=BrokenConnector(),
        anthropic_api_key="fake-key",
        model="claude-haiku-4-5-20251001",
    )
    assert response.status == "error"


# ---------------------------------------------------------------------------
# Test 3: malformed LLM output yields an error response
# ---------------------------------------------------------------------------


async def test_malformed_llm_output_handled(mock_claude_mode):
    with patch(
        "app.skills.prospect_research.call_claude", side_effect=Exception("bad output")
    ):
        response = await prospect_research.run(
            company_name="TestCo",
            notes="",
            connector=MockConnector(),
            anthropic_api_key="fake-key",
            model="claude-haiku-4-5-20251001",
        )
    assert response.status in ("error", "degraded")


# ---------------------------------------------------------------------------
# Test 4: markdown fences and preamble text are stripped before parsing
# ---------------------------------------------------------------------------


def test_markdown_fence_stripped():
    raw = 'Here is the brief:\n```json\n{"company_name": "Test"}\n```'

    # Replicate the stripping logic from prospect_research.run
    raw = raw.strip()
    if raw.startswith("```"):
        raw = raw.split("\n", 1)[-1]
        raw = raw.rsplit("```", 1)[0].strip()

    # Also handle preamble before the JSON object
    start = raw.find("{")
    end = raw.rfind("}")
    if start != -1 and end != -1:
        raw = raw[start : end + 1]

    parsed = json.loads(raw)
    assert parsed["company_name"] == "Test"


# ---------------------------------------------------------------------------
# Test 5: MockConnector returns known company data for "vercel"
# ---------------------------------------------------------------------------


async def test_mock_connector_returns_known_company():
    result = await MockConnector().search_company("vercel")
    assert result["name"] == "Vercel"
    assert result["domain"] == "vercel.com"


# ---------------------------------------------------------------------------
# Test 6: MockConnector is deterministic for unknown companies
# ---------------------------------------------------------------------------


async def test_mock_connector_deterministic():
    connector = MockConnector()
    first = await connector.search_company("randomcompany")
    second = await connector.search_company("randomcompany")
    assert first == second


# ---------------------------------------------------------------------------
# Test 7: middleware rejects payloads larger than 64 KB
# ---------------------------------------------------------------------------


async def test_middleware_rejects_large_payload():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        big_body = "x" * (65 * 1024)
        resp = await client.post(
            "/skill/research",
            content=big_body,
            headers={
                "content-type": "application/json",
                "content-length": str(len(big_body)),
            },
        )
    assert resp.status_code == 413


# ---------------------------------------------------------------------------
# Test 8: /health endpoint returns status ok
# ---------------------------------------------------------------------------


async def test_health_endpoint():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.get("/health")
    assert resp.status_code == 200
    assert resp.json()["status"] == "ok"


# ---------------------------------------------------------------------------
# Test 9: empty company_name returns 422
# ---------------------------------------------------------------------------


async def test_empty_company_name_returns_422():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.post(
            "/skill/research",
            json={"company_name": ""},
            headers={"X-Api-Key": settings.skill_api_key},
        )
    assert resp.status_code == 422


# ---------------------------------------------------------------------------
# Test 10: whitespace-only company_name returns 422
# ---------------------------------------------------------------------------


async def test_whitespace_only_company_name_returns_422():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.post(
            "/skill/research",
            json={"company_name": "   "},
            headers={"X-Api-Key": settings.skill_api_key},
        )
    assert resp.status_code == 422


# ---------------------------------------------------------------------------
# Test 11: missing X-Api-Key header returns 401
# ---------------------------------------------------------------------------


async def test_missing_api_key_returns_401():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.post(
            "/skill/research",
            json={"company_name": "TestCo"},
        )
    assert resp.status_code == 401


# ---------------------------------------------------------------------------
# Test 12: wrong X-Api-Key returns 401
# ---------------------------------------------------------------------------


async def test_wrong_api_key_returns_401():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.post(
            "/skill/research",
            json={"company_name": "TestCo"},
            headers={"X-Api-Key": "wrong-key-value"},
        )
    assert resp.status_code == 401


# ---------------------------------------------------------------------------
# Test 13: correct key + valid body reaches skill layer (not 401/422)
# ---------------------------------------------------------------------------


async def test_valid_request_reaches_skill_layer():
    mock_response = ResearchResponse(
        status="degraded",
        error="mocked — no real Claude call",
    )
    with patch.object(
        prospect_research, "run", new_callable=AsyncMock, return_value=mock_response
    ):
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            resp = await client.post(
                "/skill/research",
                json={"company_name": "TestCo"},
                headers={"X-Api-Key": settings.skill_api_key},
            )
    assert resp.status_code == 200


# ---------------------------------------------------------------------------
# Test 14: run returns "ok" even when create_note raises
# ---------------------------------------------------------------------------


async def test_run_ok_when_create_note_raises(mock_claude_mode):
    connector = MockConnector()
    with patch.object(
        connector, "create_note", side_effect=RuntimeError("write failed")
    ):
        response = await prospect_research.run(
            company_name="TestCo",
            notes="",
            connector=connector,
            anthropic_api_key="fake-key",
            model="claude-haiku-4-5-20251001",
        )
    assert response.status == "ok"
    assert response.data is not None


# ---------------------------------------------------------------------------
# Test 15: company_name is normalized back to searched name when Claude expands it
# ---------------------------------------------------------------------------


async def test_company_name_normalized_to_searched_name(mock_claude_mode):
    connector = MockConnector()
    response = await prospect_research.run(
        company_name="AWS",
        notes="",
        connector=connector,
        anthropic_api_key="fake-key",
        model="claude-haiku-4-5-20251001",
    )
    # Mock returns "TestCo" — ratio vs "AWS" is low — should normalize to "AWS"
    assert response.status == "ok"
    assert response.data.company_name == "AWS"


# ---------------------------------------------------------------------------
# Test 16: rate limit returns 429 after exceeding limit
# ---------------------------------------------------------------------------


async def test_rate_limit_returns_429(monkeypatch):
    from app import middleware
    from app.config import settings

    monkeypatch.setattr(settings, "rate_limit_requests", 1)
    monkeypatch.setattr(settings, "rate_limit_window_seconds", 60)

    # Clear bucket state for a clean test
    middleware._buckets.clear()

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # First request should pass
        resp1 = await client.post(
            "/skill/research",
            json={"company_name": "TestCo"},
            headers={"X-Api-Key": settings.skill_api_key},
        )
        assert resp1.status_code != 429

        # Second request should be rate limited
        resp2 = await client.post(
            "/skill/research",
            json={"company_name": "TestCo"},
            headers={"X-Api-Key": settings.skill_api_key},
        )
        assert resp2.status_code == 429

    # Clean up
    middleware._buckets.clear()
