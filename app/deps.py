from __future__ import annotations

from .config import settings
from .connectors.base import ResearchConnector


def get_connector() -> ResearchConnector:
    """Factory that creates a connector per call.

    Wired into FastAPI via ``Depends(get_connector)`` so each request
    gets its own connector instance — no shared global state.
    """
    if settings.connector_mode == "mock":
        from .connectors.mock import MockConnector

        return MockConnector()

    if settings.connector_mode == "hubspot":
        from .connectors.hubspot import HubSpotConnector

        return HubSpotConnector(api_key=settings.hubspot_api_key)

    raise RuntimeError(f"Unknown CONNECTOR_MODE: {settings.connector_mode}")
