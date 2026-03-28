# Backlog

Severity ratings: **Blocker** | **Critical** | **Major** | **Minor** | **Chore**

-----

## Critical

- [ ] **Develop more tests** — Playwright E2E (sessionStorage, tab switching, form submission); integration test for full research → proposal pipeline; load tests for rate limiter behavior under concurrent requests
- [ ] **Timeout handling** — no explicit timeout on Claude API calls; a slow API response hangs the request indefinitely; fix: `httpx` timeout parameter in `claude_client.py`
- [ ] **Mid-request refresh** — loading state should cancel cleanly on refresh; last successful result should restore from sessionStorage

-----

## Major

- [ ] **Rate limiter Redis upgrade** — in-memory bucket resets on deploy and doesn't share state across workers; single-worker Railway deployment is fine at current scale; Redis is the upgrade path
- [ ] **Sentry error tracking** — automatic exception capture with request context, stack traces, and alerting; three-line integration via `sentry_sdk`
- [ ] **Structured JSON logging** — replace plain-string logs with `{"level", "request_id", "skill", "message"}` format; makes logs searchable in any observability platform
- [ ] **Correlation/request IDs** — assign unique ID to every request; include in all log lines and error responses; enables full request tracing when something breaks
- [ ] **API versioning** — `/v1/research` instead of `/research`; standard practice before external callers depend on the contract
- [ ] **Contact info fields** — add `website`, `linkedin_url`, `contact_email` to `ProspectSummary`; lets a rep go from research to outreach without switching tools
- [ ] **Save to CRM button** — optional write-back per prospect; rep decides when to save rather than automatic on every research run
- [ ] **Configurable prompts** — swap system prompts per customer or use case without code changes
- [ ] **Rep voice profiles skill** — capture rep writing style; proposals output in the rep's voice rather than a generic template
- [ ] **Lead generator skill** — given a target profile, surface companies that match
- [ ] **Batch research** — process a list of companies in one request
- [ ] **Copy to clipboard** — on pitch email and subject line fields
- [ ] **Channel fit scoring** — automatically match prospect to the best outreach channels; removes judgment call from the rep
- [ ] **Error alerting** — webhook alerting on 5xx errors for immediate visibility

-----

## Minor

- [ ] **CORS configuration** — explicit allowed origins rather than open; standard for any API with a browser frontend
- [ ] **Confidence label** — clarify what it represents or remove it
- [ ] **Standalone proposal mode** — accept prospect data directly without requiring prior research run
- [ ] **Clear session button** — wipe sessionStorage manually without closing the tab
- [ ] **Loading state improvement** — progress indicator during Claude calls; currently a spinner with no feedback
- [ ] **API key rotation** — mechanism to rotate keys without downtime
- [ ] **Competitor research flag** — surface whether prospect is already advertising with a competitor

-----

## Chore

- [ ] **CI/CD GitHub Actions** — run pytest and ruff on every PR
- [ ] **`.env.example` audit** — confirm all required and optional vars are documented
- [ ] **Railway environment variable audit** — confirm production and staging parity
- [ ] **Update docs** — document Redis as upgrade path for rate limiter in ARCHITECTURE.md
- [ ] **PR title convention** — establish and document convention for consistent changelog generation
- [ ] **Git tagging** — tag releases after merging to main: `git tag v0.x.0 && git push origin v0.x.0`; aligns with CHANGELOG versioning
- [ ] **Pydantic V2 config migration** — update `Settings` class in `app/config.py` from `Config` inner class pattern to `model_config = ConfigDict(...)`; harmless deprecation warning now, breaks in Pydantic V3
- [ ] **Main branch protection** — require PR before merging to main, disable direct pushes; enforce via GitHub branch protection rules
