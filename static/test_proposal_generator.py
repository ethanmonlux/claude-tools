from __future__ import annotations

from unittest.mock import AsyncMock, patch

from httpx import ASGITransport, AsyncClient

from app.config import settings
from app.connectors.mock import MockConnector
from app.main import app
from app.models import ProposalResponse, ProspectSummary
from app.skills import proposal_generator


_VALID_PROSPECT = ProspectSummary(
    company_name="TestCo",
    industry="Developer Tools",
    estimated_size="50-200 employees",
    what_they_do="They build developer tools.",
    likely_pain_points=["scaling", "hiring"],
    why_fits="Tech audience overlap",
    suggested_subject_line="Quick question",
    confidence="high",
)

_VALID_PROPOSAL_JSON = {
    "pitch_email_body": "Hi TestCo team, ...",
    "suggested_channels": ["developer newsletter", "technical blog", "LinkedIn"],
    "talking_points": ["Point 1", "Point 2", "Point 3"],
    "follow_up_hook": "Saw your recent launch — would love to chat.",
}

_PROPOSAL_REQUEST_BODY = {
    "company_name": "TestCo",
    "prospect_data": _VALID_PROSPECT.model_dump(),
}


# ---------------------------------------------------------------------------
# Test 1: degraded response when no API key is provided
# ---------------------------------------------------------------------------


async def test_run_no_api_key():
    connector = MockConnector()
    response = await proposal_generator.run(
        company_name="TestCo",
        prospect_data=_VALID_PROSPECT,
        connector=connector,
        anthropic_api_key="",
        model="claude-haiku-4-5-20251001",
    )
    assert response.status == "degraded"
    assert response.data is None
    assert response.error is not None


# ---------------------------------------------------------------------------
# Test 2: malformed LLM output yields an error response
# ---------------------------------------------------------------------------


async def test_malformed_llm_output_handled():
    with patch("app.claude_client.call_claude", side_effect=Exception("bad output")):
        response = await proposal_generator.run(
            company_name="TestCo",
            prospect_data=_VALID_PROSPECT,
            connector=MockConnector(),
            anthropic_api_key="fake-key",
            model="claude-haiku-4-5-20251001",
        )
    assert response.status in ("error", "degraded")


# ---------------------------------------------------------------------------
# Test 3: wrong X-Api-Key returns 401
# ---------------------------------------------------------------------------


async def test_wrong_api_key_returns_401():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.post(
            "/skill/proposal",
            json=_PROPOSAL_REQUEST_BODY,
            headers={"X-Api-Key": "wrong-key-value"},
        )
    assert resp.status_code == 401


# ---------------------------------------------------------------------------
# Test 4: missing X-Api-Key header returns 401
# ---------------------------------------------------------------------------


async def test_missing_api_key_returns_401():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.post(
            "/skill/proposal",
            json=_PROPOSAL_REQUEST_BODY,
        )
    assert resp.status_code == 401


# ---------------------------------------------------------------------------
# Test 5: correct key + valid body reaches skill layer (not 401/422)
# ---------------------------------------------------------------------------


async def test_valid_request_reaches_skill_layer():
    mock_response = ProposalResponse(
        status="degraded",
        error="mocked — no real Claude call",
    )
    with patch.object(
        proposal_generator, "run", new_callable=AsyncMock, return_value=mock_response
    ):
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            resp = await client.post(
                "/skill/proposal",
                json=_PROPOSAL_REQUEST_BODY,
                headers={"X-Api-Key": settings.skill_api_key},
            )
    assert resp.status_code == 200


# ---------------------------------------------------------------------------
# Test 6: company name mismatch returns error
# ---------------------------------------------------------------------------


async def test_company_name_mismatch_returns_error():
    connector = MockConnector()
    response = await proposal_generator.run(
        company_name="WrongCo",
        prospect_data=_VALID_PROSPECT,
        connector=connector,
        anthropic_api_key="fake-key",
        model="claude-haiku-4-5-20251001",
    )
    assert response.status == "error"
    assert "does not match" in response.error.lower()


# ---------------------------------------------------------------------------
# Test 7: empty company name returns 422
# ---------------------------------------------------------------------------


async def test_empty_company_name_returns_422():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.post(
            "/skill/proposal",
            json={
                "company_name": "",
                "prospect_data": _VALID_PROSPECT.model_dump(),
            },
            headers={"X-Api-Key": settings.skill_api_key},
        )
    assert resp.status_code == 422


# ---------------------------------------------------------------------------
# Test 8: 65KB payload returns 413
# ---------------------------------------------------------------------------


async def test_large_payload_returns_413():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        big_body = "x" * (65 * 1024)
        resp = await client.post(
            "/skill/proposal",
            content=big_body,
            headers={
                "content-type": "application/json",
                "content-length": str(len(big_body)),
            },
        )
    assert resp.status_code == 413


# ---------------------------------------------------------------------------
# Test 9: happy path returns ok with data
# ---------------------------------------------------------------------------


async def test_happy_path_returns_ok_with_data(mock_claude_mode):
    response = await proposal_generator.run(
        company_name="TestCo",
        prospect_data=_VALID_PROSPECT,
        connector=MockConnector(),
        anthropic_api_key="fake-key",
        model="claude-haiku-4-5-20251001",
    )
    assert response.status == "ok"
    assert response.data is not None
    assert response.data.pitch_email_body is not None
    assert len(response.data.suggested_channels) > 0
    assert len(response.data.talking_points) > 0
    assert response.data.follow_up_hook is not None


# ---------------------------------------------------------------------------
# Test 10: rate limit returns 429 after exceeding limit
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
            "/skill/proposal",
            json=_PROPOSAL_REQUEST_BODY,
            headers={"X-Api-Key": settings.skill_api_key},
        )
        assert resp1.status_code != 429

        # Second request should be rate limited
        resp2 = await client.post(
            "/skill/proposal",
            json=_PROPOSAL_REQUEST_BODY,
            headers={"X-Api-Key": settings.skill_api_key},
        )
        assert resp2.status_code == 429

    # Clean up
    middleware._buckets.clear()
