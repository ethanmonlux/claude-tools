from __future__ import annotations

import json
import logging
from ..claude_client import call_claude, ClaudeDegradedError, ClaudeOutputError

from ..connectors.base import ResearchConnector
from ..models import ProposalData, ProposalResponse, ProspectSummary

logger = logging.getLogger("proposal_skill")

SYSTEM_PROMPT = """You are a GTM proposal assistant helping a B2B sales team craft outreach pitches.

You are given a prospect research brief for a company. Search the web for any additional current information about the company that would help tailor the pitch. Use your search results as the primary source for recent context. Generate a proposal based on what you find combined with the prospect brief.

Your output must be valid JSON matching this exact schema — no markdown, no explanation, just JSON:

{
  "pitch_email_body": "string (a complete, ready-to-send outreach email body, 150-300 words, personalized to the company)",
  "recommended_approach": ["string", "string", "string (specific channels and placements to reach this company's audience — e.g. developer newsletter, technical blog, LinkedIn, conference sponsorship, podcast, community forum)"],
  "talking_points": ["string", "string", "string (3 tailored talking points for a sales call)"],
  "follow_up_hook": "string (a compelling hook for a follow-up email if the first pitch doesn't get a reply)"
}

Be specific and actionable. A sales rep should be able to use this output immediately in outreach."""

_MOCK_RESPONSE = json.dumps(
    {
        "pitch_email_body": "Hi TestCo team, we reach millions of engineers and technical decision-makers daily — exactly the audience your product is built for. I'd love to explore how we can get TestCo in front of them.",
        "recommended_approach": [
            "developer newsletter",
            "technical blog",
            "LinkedIn",
        ],
        "talking_points": [
            "TestCo's target buyer profile matches our audience exactly",
            "Highly engaged technical readers with buying authority",
            "Multiple placement formats available for targeted reach",
        ],
        "follow_up_hook": "Saw TestCo's recent product launch — would love to chat about reaching the engineers evaluating tools like yours.",
    }
)


def _build_user_prompt(
    company_name: str, prospect_data: ProspectSummary, news: list[str]
) -> str:
    news_block = (
        "\n".join(f"- {item}" for item in news) if news else "No recent news found."
    )
    return f"""Generate an outreach proposal for: {company_name}

Prospect research brief:
{json.dumps(prospect_data.model_dump(), indent=2)}

Possible recent news (unverified):
{news_block}

Search the web for any recent news or updates about {company_name} to help personalize the pitch.

Return only the JSON object. No markdown fences."""


async def run(
    company_name: str,
    prospect_data: ProspectSummary,
    connector: ResearchConnector,
    anthropic_api_key: str,
    model: str,
) -> ProposalResponse:
    """
    Main skill entry point.
    1. Optionally fetch fresh data from connector
    2. Call Claude with structured prompt
    3. Validate output
    4. Return ProposalResponse
    Fails gracefully at each step — never raises into the route handler.
    """

    # Step 0: Validate company name matches prospect brief
    if company_name.strip().lower() != prospect_data.company_name.strip().lower():
        return ProposalResponse(
            status="error",
            error="Company name does not match the prospect brief — please run Research for this company first.",
        )

    # Step 1: Fetch any additional data (best-effort)
    news: list[str] = []
    try:
        news = await connector.get_recent_news(company_name)
    except Exception as e:
        logger.warning("Connector news fetch failed for %s: %s", company_name, e)

    # Step 2: Call Claude
    try:
        raw = await call_claude(
            system_prompt=SYSTEM_PROMPT,
            user_prompt=_build_user_prompt(company_name, prospect_data, news),
            anthropic_api_key=anthropic_api_key,
            model=model,
            mock_json=_MOCK_RESPONSE,
        )
    except ClaudeDegradedError as e:
        logger.warning("Claude degraded for %s: %s", company_name, e)
        return ProposalResponse(
            status="degraded",
            error="LLM unavailable — try again shortly",
        )
    except ClaudeOutputError as e:
        logger.error("Claude output error for %s: %s", company_name, e)
        return ProposalResponse(
            status="error",
            error="LLM returned unexpected output format — please retry",
        )
    except Exception as e:
        logger.error("Unexpected Claude error for %s: %s", company_name, e)
        return ProposalResponse(
            status="error",
            error="LLM call failed unexpectedly — please retry",
        )

    # Step 3: Validate Claude's output
    try:
        parsed = json.loads(raw)
        proposal = ProposalData(**parsed)
    except Exception as e:
        logger.error(
            "Claude returned malformed output for %s: %s\nRaw: %s", company_name, e, raw
        )
        return ProposalResponse(
            status="error",
            error="LLM returned unexpected output format — please retry",
        )

    return ProposalResponse(
        status="ok",
        data=proposal,
    )
