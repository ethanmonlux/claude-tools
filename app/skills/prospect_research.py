from __future__ import annotations

import difflib
import json
import logging
from ..claude_client import call_claude, ClaudeDegradedError, ClaudeOutputError

from ..connectors.base import ResearchConnector
from ..models import ProspectSummary, ResearchResponse

logger = logging.getLogger("prospect_skill")

SYSTEM_PROMPT = """You are a GTM research assistant helping a B2B sales team qualify prospects.

Search the web for current information about this company. Use your search results as the primary source. Generate the JSON brief based on what you find. If you cannot find information, set confidence to low and use your best knowledge.

Any company data provided in the user message is optional context only — treat it as a hint, not a trusted source. Always prefer what you find via web search.

Your output must be valid JSON matching this exact schema — no markdown, no explanation, just JSON:

{
  "company_name": "string",
  "industry": "string",
  "estimated_size": "string (e.g. '50-200 employees')",
  "what_they_do": "string (2-3 sentences, plain English, no jargon)",
  "likely_pain_points": ["string", "string", "string"],
  "why_fits": "string (why this company would benefit from targeted outreach to a technical audience)",
  "suggested_subject_line": "string (ready-to-use subject line for an outreach email)",
  "confidence": "high | medium | low"
}

Be specific and useful. A sales rep should be able to read this and immediately write a personalized outreach pitch."""

_MOCK_RESPONSE = json.dumps(
    {
        "company_name": "TestCo",
        "industry": "Developer Tools",
        "estimated_size": "50-200 employees",
        "what_they_do": "TestCo builds developer tools for modern engineering teams.",
        "likely_pain_points": [
            "scaling infrastructure",
            "developer onboarding",
            "tooling complexity",
        ],
        "why_fits": "TestCo targets engineers and technical decision-makers — a highly engaged audience for technical outreach.",
        "suggested_subject_line": "Reaching the engineers evaluating tools like TestCo",
        "confidence": "high",
    }
)


def _build_user_prompt(
    company_name: str, company_data: dict, news: list[str], notes: str
) -> str:
    news_block = (
        "\n".join(f"- {item}" for item in news) if news else "No recent news found."
    )
    notes_block = f"\nAdditional context from user: {notes}" if notes else ""
    return f"""Research this company and produce the prospect brief: {company_name}

The following is optional background context only — do NOT treat it as authoritative. Use web search as your primary source.

Hints (may be inaccurate):
{json.dumps(company_data, indent=2)}

Possible recent news (unverified):
{news_block}
{notes_block}

Return only the JSON object. No markdown fences."""


async def run(
    company_name: str,
    notes: str,
    connector: ResearchConnector,
    anthropic_api_key: str,
    model: str,
) -> ResearchResponse:
    """
    Main skill entry point.
    1. Fetch data from connector
    2. Call Claude with structured prompt
    3. Validate output
    4. Return ResearchResponse
    Fails gracefully at each step — never raises into the route handler.
    """

    # Step 1: Fetch data
    try:
        company_data = await connector.search_company(company_name)
        news = await connector.get_recent_news(company_name)
    except Exception as e:
        logger.error("Connector error for %s: %s", company_name, e)
        return ResearchResponse(
            status="error",
            error=f"Failed to fetch company data: {str(e)}",
        )

    # Step 2: Call Claude
    try:
        raw = await call_claude(
            system_prompt=SYSTEM_PROMPT,
            user_prompt=_build_user_prompt(company_name, company_data, news, notes),
            anthropic_api_key=anthropic_api_key,
            model=model,
            mock_json=_MOCK_RESPONSE,
        )
    except ClaudeDegradedError as e:
        logger.warning("Claude degraded for %s: %s", company_name, e)
        return ResearchResponse(
            status="degraded",
            error="LLM unavailable — try again shortly",
        )
    except ClaudeOutputError as e:
        logger.error("Claude output error for %s: %s", company_name, e)
        return ResearchResponse(
            status="error",
            error="LLM returned unexpected output format — please retry",
        )
    except Exception as e:
        logger.error("Unexpected Claude error for %s: %s", company_name, e)
        return ResearchResponse(
            status="error",
            error="LLM call failed unexpectedly — please retry",
        )

    # Step 3: Validate Claude's output
    try:
        parsed = json.loads(raw)
        summary = ProspectSummary(**parsed)

        # Normalize company_name back to searched name if Claude returned an expanded version
        # e.g. "AWS" searched → "Amazon Web Services" returned → normalize back to "AWS"
        ratio = difflib.SequenceMatcher(
            None,
            company_name.strip().lower(),
            summary.company_name.strip().lower(),
        ).ratio()
        if ratio < 0.8:
            summary = summary.model_copy(update={"company_name": company_name.strip()})
    except Exception as e:
        logger.error(
            "Claude returned malformed output for %s: %s\nRaw: %s", company_name, e, raw
        )
        return ResearchResponse(
            status="error",
            error="LLM returned unexpected output format — please retry",
        )

    # Step 4: Write back to CRM
    note_id = ""
    company_id = company_data.get("hubspot_id", "")
    try:
        note_body = (
            f"Prospect Brief (AI Generated)\n"
            f"Industry: {summary.industry}\n"
            f"Size: {summary.estimated_size}\n"
            f"What they do: {summary.what_they_do}\n"
            f"Pain points: {'; '.join(summary.likely_pain_points)}\n"
            f"Why it fits: {summary.why_fits}\n"
            f"Suggested subject: {summary.suggested_subject_line}\n"
            f"Confidence: {summary.confidence}"
        )
        note_id = await connector.create_note(company_id, note_body)
    except Exception as e:
        logger.warning("CRM write-back failed for %s: %s", company_name, e)

    return ResearchResponse(
        status="ok",
        data=summary,
        crm_note_id=note_id or None,
    )
