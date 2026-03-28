# Changelog

All notable changes to Claude Tools are documented here.
Format: [Keep a Changelog](https://keepachangelog.com/en/1.0.0/)

---

## [1.0.0] — 2026-03-28

### Added
- Prospect research tool (POST /skill/research) — accepts company name and optional notes, returns structured brief via Claude with web search
- Proposal generator tool (POST /skill/proposal) — takes prospect research output and generates pitch email, channel suggestions, talking points, and follow-up hook
- Connector abstraction — CONNECTOR_MODE=mock or hubspot via one env var, no code changes
- Mock connector with deterministic fixture data — clone and run in 2 minutes, no credentials needed
- HubSpot connector — search company, read CRM data, write note back on research completion
- Pydantic validation on all Claude output — treats LLM responses like untrusted user input
- Graceful degradation — four failure modes, four clean responses; never a stack trace
- Per-key token bucket rate limiting — 10 requests per 60 seconds, configurable
- HMAC-safe API key auth — fail-closed, 401 before any skill logic runs
- RequestSizeLimitMiddleware — 64KB limit on skill endpoints
- Shared Claude call helper (app/claude_client.py) — all Claude API calls go through one place
- Company name fuzzy matching — normalizes expanded names back to searched term
- Two-tab frontend (Research + Proposal) served directly by FastAPI — no build pipeline
- sessionStorage persistence — session data clears on tab close
- CLAUDE_MODE=mock — skips Anthropic API entirely for local dev and staging
- n8n pipeline — three workflows: manual test run, form-triggered research, form-triggered proposal
- 26 tests covering auth, validation, happy path, and all failure modes
- CLAUDE.md constraint document for Claude Code sessions
- ARCHITECTURE.md with system diagram and design decisions
- docs/DEPLOY.md — production deployment checklist
