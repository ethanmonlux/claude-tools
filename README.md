# Claude Tools

Built as a working demonstration for TLDR's first AI Engineer role. Two Claude Skills — prospect research and proposal generation — deployed on TLDR's stack (FastAPI, Railway), connected via n8n, accessible to non-technical users without code or engineering tickets. It's live at https://tldr-skills-production.up.railway.app.

## How to Use

1. Go to https://tldr-skills-production.up.railway.app
2. Enter the API key (get this from your team)
3. **Research tab** — type a company name (e.g. "Datadog"), optionally add a note, click Research to get a prospect brief
4. **Proposal tab** — after researching a company, click Generate Proposal to get a ready-to-send pitch email, talking points, and follow-up hook

**Non-technical workflow (n8n):** A sales rep fills out a form, gets a complete prospect brief posted to Discord — no API key, no code, no engineering ticket. The skill has no idea n8n is calling it. That's composability working in practice.

**Composability:** `company name → [Research Skill] → ProspectSummary → [Proposal Skill] → pitch email`. The output schema of one skill is the exact input schema of the next.

**Tests:** 26 tests — most cover failure modes, not the happy path. Production systems break on edge cases.

## Live Demo

Running at: https://tldr-skills-production.up.railway.app

The UI handles auth automatically. For direct API calls, include the `X-Api-Key` header.

> ⚠️ The live instance is public-facing. Auth is the only gate — do not share the API key publicly.

## Local Development

```bash
cp .env.example .env
# Add ANTHROPIC_KEY to .env

pip install -e .
uvicorn app.main:app --reload --port 8080
# Open http://localhost:8080
```

## Architecture

```
User (browser)
    │
    ▼
static/index.html          Simple HTML/JS frontend, no framework
    │
    ├──▶ POST /skill/research    FastAPI route with key auth
    │         │
    │         ▼
    │    app/skills/
    │      prospect_research.py  Research skill logic
    │
    └──▶ POST /skill/proposal    FastAPI route with key auth
              │
              ▼
         app/skills/
           proposal_generator.py Proposal skill logic
              │
              ├── app/connectors/    External data (mock or HubSpot)
              │     base.py          Protocol definition
              │     mock.py          Fixture data, no credentials needed
              │     hubspot.py       Real HubSpot API (set CONNECTOR_MODE=hubspot)
              │
              ├── app/claude_client.py  Shared Claude call helper — API call, output cleaning, typed errors
              │
              └── Anthropic API      Claude synthesizes → structured JSON output
```

### Design Principles

**Connector abstraction** — All external API calls go through `app/connectors/base.py` (a Protocol). Skill logic never calls APIs directly. Swap `mock` → `hubspot` with one env var, no code changes.

**Fail-graceful LLM** — If Claude is unavailable or returns malformed output, the API returns a structured error response. It never crashes the server or returns a 500.

**Validated structured output** — Claude's response is parsed and validated with Pydantic before returning. Malformed LLM output surfaces as a clear `status: error` with a human-readable message.

**Operator surface** — `GET /health` shows current mode. The UI clearly labels all output as AI-generated.

**Business-specific output** — Every brief includes a `why_fits` field that answers the rep's actual question: why would this company be a good outreach target? Generic research tools return company info. This field returns a pitch angle.

## API

### POST /skill/research

**Headers:** `X-Api-Key: <SKILL_API_KEY>`

**Request:**

```json
{
  "company_name": "Vercel",
  "notes": "Focus on their AI initiatives"
}
```

**Response:**

```json
{
  "status": "ok",
  "ai_generated": true,
  "data": {
    "company_name": "Vercel",
    "industry": "Developer Tools / Cloud Infrastructure",
    "estimated_size": "201-500 employees",
    "what_they_do": "...",
    "likely_pain_points": ["...", "...", "..."],
    "why_fits": "...",
    "suggested_subject_line": "...",
    "confidence": "high"
  }
}
```

### POST /skill/proposal

**Headers:** `X-Api-Key: <SKILL_API_KEY>`

**Request:**

```json
{
  "company_name": "Vercel",
  "prospect_data": {
    "company_name": "Vercel",
    "industry": "Developer Tools / Cloud Infrastructure",
    "estimated_size": "201-500 employees",
    "what_they_do": "...",
    "likely_pain_points": ["...", "...", "..."],
    "why_fits": "...",
    "suggested_subject_line": "...",
    "confidence": "high"
  }
}
```

**Response:**

```json
{
  "status": "ok",
  "ai_generated": true,
  "data": {
    "pitch_email_body": "...",
    "suggested_channels": ["developer newsletter", "technical blog", "LinkedIn"],
    "talking_points": ["...", "...", "..."],
    "follow_up_hook": "..."
  }
}
```

## Configuration

|Variable           |Default  |Description                    |
|-------------------|---------|-------------------------------|
|`SKILL_API_KEY`    |required |Auth key for the API — startup fails if not set |
|`ANTHROPIC_KEY`    |—        |Required for live Claude calls |
|`ANTHROPIC_MODEL`  |`claude-haiku-4-5-20251001`|Claude model to use |
|`CONNECTOR_MODE`   |`mock`   |`mock` or `hubspot`            |
|`HUBSPOT_API_KEY`  |—        |Required when mode is `hubspot`|
|`CLAUDE_MODE`      |`live`   |`live` or `mock` — mock skips Anthropic API, returns fixture data |
|`RATE_LIMIT_REQUESTS`|`10`   |Max requests per window per API key |
|`RATE_LIMIT_WINDOW_SECONDS`|`60`|Rate limit window in seconds |

## Extending

To add a new data source:

1. Add a method to `app/connectors/base.py` (the Protocol)
2. Implement it in `app/connectors/hubspot.py`
3. Add a fixture return in `app/connectors/mock.py`
4. Use it in the relevant skill under `app/skills/`
