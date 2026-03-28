# Deploying to Production

Reference for every merge to main. Run through this in order.

-----

## 1. Before Merging

**Local checks — both must pass:**

```bash
SKILL_API_KEY=test-key python -m pytest
ruff check .
```

**Repo hygiene:**

- [ ] No `.env` committed — `git log --all -- .env` returns nothing
- [ ] `[Unreleased]` in CHANGELOG.md is empty or has been cut to a version
- [ ] TODO.md is current — completed items marked ✅, new items added

-----

## 2. Merge

dev → staging → main

Railway auto-deploys from main on push. Wait for deploy to complete before running checks.

-----

## 3. After Deploy — Production Verification

**URL:** https://tldr-skills-production.up.railway.app

- [ ] Page loads
- [ ] Enter demo API key — accepted, no 401
- [ ] Research tab — type a real company (Datadog, Vercel, AWS) — brief returns
- [ ] Proposal tab — generate proposal from research result — pitch email returns
- [ ] Refresh page — API key and results restore from sessionStorage
- [ ] `/health` endpoint returns `status: ok`
- [ ] `/docs` endpoint loads FastAPI docs

-----

## 4. Railway Environment Variable Audit

Verify production has all required vars set correctly:

|Variable                   |Expected                              |
|---------------------------|--------------------------------------|
|`SKILL_API_KEY`            |demo key (matches what's in the email)|
|`ANTHROPIC_KEY`            |real Anthropic key                    |
|`CLAUDE_MODE`              |`live`                                |
|`CONNECTOR_MODE`           |`mock` (until HubSpot is wired)       |
|`ANTHROPIC_MODEL`          |`claude-haiku-4-5-20251001`           |
|`RATE_LIMIT_REQUESTS`      |`10`                                  |
|`RATE_LIMIT_WINDOW_SECONDS`|`60`                                  |

-----

## Rollback

If production breaks after a merge:

1. `git revert HEAD` on main
1. Push — Railway auto-deploys the revert
1. Investigate on develop before re-merging
