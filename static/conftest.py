from __future__ import annotations

import pytest

from app.connectors.mock import MockConnector
from app.deps import get_connector
from app.main import app


@pytest.fixture(autouse=True)
def _override_connector():
    """Replace the connector dependency with MockConnector for every test."""
    mock = MockConnector()
    app.dependency_overrides[get_connector] = lambda: mock
    yield
    app.dependency_overrides.clear()


@pytest.fixture
def mock_claude_mode(monkeypatch):
    """Set CLAUDE_MODE=mock for tests that should not hit the Anthropic API."""
    monkeypatch.setenv("CLAUDE_MODE", "mock")
    from app.config import settings

    monkeypatch.setattr(settings, "claude_mode", "mock")
    yield
    monkeypatch.setattr(settings, "claude_mode", "live")
