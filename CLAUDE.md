# Claude Tools — Claude Code Context

> **Start here every session.** Read this file before touching any code.

## Project

Two composable AI tools — prospect research and proposal generation — deployed on FastAPI and Railway. Research tool: input a company name → web search → Claude synthesizes → structured prospect brief. Proposal tool: input a prospect brief → Claude generates → ready-to-send outreach pitch. Built as a production demonstration of composable AI tools accessible to non-technical teammates without code or engineering tickets.

## Safety Rules (non-negotiable)

- Never send PII or credentials to the Anthropic API
- Always validate Claude's structured output before returning it to the caller — if Claude returns malformed JSON, fail gracefully with a clear error, not a 500
- Fail-silent on LLM errors: if Claude is unavailable, return a degraded response, never crash the server
- Label all AI-generated output clearly in the response payload
- Never log API keys, tokens, or secrets
- Never commit or expose SKILL_API_KEY — the live Railway instance is public-facing and key auth is the only gate. Rotate the key before sharing the URL broadly.

## Workflow Rules

- Always plan before implementing. Before writing any code, list every file you will touch and every change you will make. Wait for explicit approval before proceeding.
- Never commit, push, or create a PR without explicit approval after showing the plan.
- Batch related changes together in a single plan when possible.
- After approval, implement the change, run pytest and ruff check, commit, and push. One prompt, one commit. You will not open a PR — the engineer opens the PR manually when the session is done.
- **Tests must pass before committing.** Never commit or push if `pytest` or `ruff check .` fails. Fix failures first, then commit.
- **Never update documentation automatically.** Do not touch CHANGELOG.md, CLAUDE.md, ARCHITECTURE.md, README.md, or TODO.md unless explicitly instructed via a CC prompt. Documentation updates are always a separate prompt issued by the engineer.

## Code Style

- Surgical edits over rewrites
- Minimal changes — don't refactor things that aren't broken
- If something is already implemented, say so and move on
- Read the relevant file before proposing any change
- Mock-first: always keep the mock connector working so the system is testable without live credentials

## Files to Always Read First

- app/main.py — app assembly, lifespan, middleware, routes
- app/models.py — input/output schemas (Pydantic)
- app/skills/prospect_research.py — core skill logic
- app/skills/proposal_generator.py — proposal generation skill logic
- app/connectors/base.py — connector protocol
- app/config.py — all settings
- app/claude_client.py — shared Claude call helper, handles API call, output cleaning, and typed error raising

## Architecture Summary

- FastAPI backend, two skill endpoints: POST /skill/research and POST /skill/proposal
- Connector layer (app/connectors/) abstracts external APIs — uses the Protocol pattern — skill logic never calls external services directly
- Mock connector always available for testing without live credentials
- Claude calls live in app/claude_client.py — shared helper used by all skills, never scattered across routes or duplicated in individual skill files
- Structured output validated with Pydantic before returning
- Static frontend served directly by FastAPI (no separate server needed)
- Fail-closed auth: requests without a valid API key are rejected at middleware

## What Is Already Implemented (do not re-implement)

- Request size limit middleware (app/middleware.py)
- Per-request connector factory (app/deps.py)
- Settings with env-based config (app/config.py)
- Mock connector returning fixture data (app/connectors/mock.py)
- HubSpot connector (app/connectors/hubspot.py)
- Prospect research skill (app/skills/prospect_research.py)
- Proposal generation skill (app/skills/proposal_generator.py)
- Two-tab frontend (Research + Proposal) served at / (static/index.html)
- Timing-safe API key comparison using hmac.compare_digest (app/main.py)
- Shared Claude call helper (app/claude_client.py) — Anthropic client creation, web search tool, text block extraction, markdown/cite stripping, JSON extraction, ClaudeDegradedError and ClaudeOutputError typed exceptions
- Per-key token bucket rate limiting (app/middleware.py) — 10 requests per 60 seconds by default, configurable via RATE_LIMIT_REQUESTS and RATE_LIMIT_WINDOW_SECONDS, returns 429 with structured error
- sessionStorage persistence (static/index.html) — research results, proposal results, company name, API key, and active tab all restored automatically on page refresh

## Connector Pattern

Connectors follow a Protocol (app/connectors/base.py). To add a new data source:

1. Add method to the Protocol
2. Implement in the real connector
3. Add a fixture return in mock.py

Never call external APIs directly from skill logic or route handlers.

## Output Schema

All skill responses include:

- `status`: "ok" | "error" | "degraded"
- `ai_generated`: true (always label LLM output)
- `data`: the structured result
- `error`: human-readable message if status != "ok"

## Pre-commit Checks

Before every commit and push, run:

- `pytest` — all tests must pass
- `ruff check .` — no lint errors allowed