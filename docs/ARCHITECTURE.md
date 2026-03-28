# Claude Tools — Architecture

## What This Is

Two composable AI tools — prospect research and proposal generation — deployed on FastAPI and Railway. The research tool takes a company name, searches the web in real time, and outputs a structured prospect brief. The proposal tool takes that brief as input and generates a ready-to-send outreach pitch. Designed as primitives in a larger tools library where outputs from one tool feed directly into the next.

## System Diagram

```
Browser (static/index.html)
        │
        ▼
POST /skill/research   ←  X-Api-Key auth
POST /skill/proposal   ←  X-Api-Key auth
        │
        ▼
RequestSizeLimitMiddleware (64KB cap, fail-closed)
RateLimitMiddleware (per-key token bucket, 10 req/60s, fail-closed)
        │
        ├──▶ prospect_research.run()
        │           │
        └──▶ proposal_generator.run()
                    │
        ┌───────────┘
        │
        ├──▶ ResearchConnector (Protocol)
        │         ├── MockConnector (no credentials)
        │         └── HubSpotConnector (CONNECTOR_MODE=hubspot)
        │
        └──▶ app/claude_client.py
                  └──▶ Anthropic API
                            ├── web_search tool (real-time data)
                            └── Cleaned JSON → Pydantic validation in skill
                            │
                            ▼
                    ResearchResponse | ProposalResponse (ok | degraded | error)
```

## Design Decisions

### 1. Connector Abstraction (Protocol Pattern)

Why: skill logic never touches external APIs directly. Swapping from mock to HubSpot is one env var change — no code touched. MockConnector means the system is always testable and demo-able without live credentials.

### 2. Web Search as Primary Data Source

Why: connector data is often stale or incomplete. Giving Claude live search results via the built-in web_search tool produces dramatically more accurate output than passing static company data. Claude searches first, synthesizes second.

### 3. Fail-Silent LLM Errors

Why: this is a sales aid, not a critical system. If Claude is unavailable, the API returns status: degraded with a human-readable message. The server never crashes. A degraded response is always better than a 500.

### 4. Pydantic Validation on Claude Output

Why: LLMs are non-deterministic. Claude sometimes wraps JSON in markdown fences, adds preamble sentences, or refuses a request entirely. Validating the schema before returning means the frontend contract is stable. Raw responses are logged on failure so behavior can be diagnosed and the prompt improved.

### 5. Explicit Prompt Guardrails

Why: Claude has opinions. Without explicit instructions it refused to research large companies like AWS, deciding they weren't valid prospects. Production skills need to tell Claude exactly what the use case is and override its assumptions. The system prompt specifies that all companies are valid prospects and explains why.

### 6. Single-File Frontend, No Framework

Why: internal tools don't need build pipelines. FastAPI serves index.html directly. Any engineer can read and edit it in 5 minutes. No npm, no webpack, no deploy step for the frontend.

### 7. Structured Output Schema

Why: machine-readable outputs mean this skill composes with downstream skills. The prospect brief can pipe directly into a proposal generator or HubSpot enrichment writer without transformation layers. This is the core of composable design.

### 8. Shared Claude Call Helper

Why: both skills duplicated the same API call, output cleaning, and error handling. A shared helper means the pattern is implemented once, tested once, and every new skill calls the helper instead of re-implementing it. ClaudeDegradedError and ClaudeOutputError give skills a clean typed interface to handle failures without knowing the implementation details.

## Failure Modes and How They're Handled

| Failure | Behavior |
|---------|----------|
| Claude unavailable | status: degraded, human-readable error |
| Claude returns malformed JSON | status: error, raw response logged |
| Claude wraps JSON in markdown | Stripped before parsing |
| Claude adds preamble text | JSON extracted by finding first { last } |
| Claude refuses the request | Logged, status: error, prompt improved |
| Connector unavailable | status: error, never crashes server |
| Bad API key | 401 before request reaches skill logic |
| Request too large | 413 from middleware before route handler |
| Rate limit exceeded | 429 from middleware, structured error response |

## What's Next — How It Extends

**HubSpot write-back:** implemented — the skill automatically creates a note on the company record after generating the brief. Requires crm.objects.notes.write scope (paid HubSpot plan). The 403 on free accounts is a plan limitation, not a bug.

**Proposal generator skill:** implemented — takes a prospect brief as input, searches the web for additional context, and outputs a draft sponsorship proposal with pitch email, newsletter suggestions, talking points, and a follow-up hook. This is the composability payoff — the output schema of the research skill becomes the input schema of the proposal skill.

**Batch mode:** process a list of companies from a CSV or HubSpot list. Same skill, different trigger.

**Slack integration:** post brief directly to a sales channel when a rep requests it.

**n8n integration:** live. Three workflows connect to these skills via HTTP node — a manual trigger for one-off research runs, a form trigger for automated research pipelines, and a full proposal pipeline (form → research → Code node → proposal → Discord). See docs/n8n/ for screenshots and setup.

## Running It

See README.md for quick start.

Key env vars:
- `ANTHROPIC_KEY` — required for live Claude calls
- `SKILL_API_KEY` — required, no default — startup fails if not set
- `CONNECTOR_MODE` — mock (default) or hubspot
- `HUBSPOT_API_KEY` — required when CONNECTOR_MODE=hubspot
- `CLAUDE_MODE` — live (default) or mock — mock skips Anthropic API entirely
- `RATE_LIMIT_REQUESTS` — max requests per window per API key (default 10)
- `RATE_LIMIT_WINDOW_SECONDS` — rate limit window in seconds (default 60)
