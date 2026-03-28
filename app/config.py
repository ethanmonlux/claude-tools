from __future__ import annotations

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # Auth
    skill_api_key: str  # Required — set SKILL_API_KEY env var or startup fails

    # Anthropic
    anthropic_key: str = ""
    anthropic_model: str = "claude-haiku-4-5-20251001"

    # HubSpot
    hubspot_api_key: str = ""

    # Connector mode: "mock" or "hubspot"
    connector_mode: str = "mock"

    # Claude mode: "live" or "mock" (mock returns fixture data without calling the API)
    claude_mode: str = "live"

    # Rate limiting (per API key, in-memory token bucket)
    rate_limit_requests: int = 10  # max requests per window
    rate_limit_window_seconds: int = 60  # window size in seconds

    # Server
    port: int = 8080

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


settings = Settings()
