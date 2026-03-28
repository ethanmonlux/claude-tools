from __future__ import annotations

import hashlib
import logging

logger = logging.getLogger(__name__)


def _pick(name: str, options: list[str]) -> str:
    """Deterministically pick an option based on the company name."""
    idx = int(hashlib.md5(name.encode()).hexdigest(), 16) % len(options)
    return options[idx]


_INDUSTRIES = [
    "Developer Tools",
    "Cybersecurity",
    "FinTech",
    "HealthTech",
    "E-Commerce / Retail Tech",
    "MarTech / AdTech",
    "Data Infrastructure",
    "EdTech",
    "HR Tech / PeopleOps",
    "Cloud Infrastructure",
]

_SIZES = [
    "1-10 employees",
    "11-50 employees",
    "51-200 employees",
    "201-500 employees",
    "501-1000 employees",
    "1001-5000 employees",
]

_DESCRIPTIONS = [
    "provides developer tools that help engineering teams automate CI/CD pipelines and streamline code review workflows",
    "offers a cloud-based cybersecurity platform that uses machine learning to detect and respond to threats in real time",
    "builds payment infrastructure and financial APIs that enable startups to embed banking features into their products",
    "develops remote patient monitoring software used by healthcare systems to improve chronic disease management",
    "operates an AI-driven personalization engine that helps online retailers increase conversion rates",
    "provides marketing attribution and analytics tools that help growth teams measure campaign ROI across channels",
    "builds a real-time data pipeline platform that simplifies streaming ETL for data engineering teams",
    "offers an adaptive learning platform used by universities and corporate training programs to personalize education",
    "develops workforce planning and talent analytics software for mid-market and enterprise HR departments",
    "provides Kubernetes-native infrastructure tooling that simplifies multi-cloud deployments",
]

_NEWS_TEMPLATES = [
    [
        "{name} raises ${amount}M Series {round} to expand into new markets",
        "{name} launches integration with {partner}",
        "{name} named to {list_name}",
    ],
    [
        "{name} reports 3x YoY revenue growth in latest earnings",
        "{name} opens new engineering hub in {city}",
        "{name} partners with {partner} on joint product initiative",
    ],
    [
        "{name} appoints former {big_co} VP as new CTO",
        "{name} crosses {users} active users milestone",
        "{name} announces SOC 2 Type II certification",
    ],
]

_AMOUNTS = ["8", "12", "24", "40", "65"]
_ROUNDS = ["A", "A", "B", "B", "C"]
_PARTNERS = ["Slack", "Notion", "Datadog", "Snowflake", "HubSpot", "Salesforce"]
_LISTS = [
    "Forbes Cloud 100 watchlist",
    "Deloitte Fast 500",
    "Inc. 5000",
    "Gartner Cool Vendors",
]
_CITIES = ["Austin", "London", "Toronto", "Berlin", "New York"]
_BIG_COS = ["Google", "Meta", "Stripe", "AWS", "Microsoft"]
_USER_COUNTS = ["10K", "50K", "100K", "500K"]


_KNOWN_COMPANIES: dict[str, dict] = {
    "vercel": {
        "name": "Vercel",
        "domain": "vercel.com",
        "industry": "Developer Tools",
        "size": "501-1000 employees",
        "description": "Vercel provides a frontend cloud platform that enables developers to build and deploy web applications with a focus on performance, scalability, and developer experience. Creator of the Next.js framework.",
        "linkedin_url": "https://linkedin.com/company/vercel",
    },
    "linear": {
        "name": "Linear",
        "domain": "linear.app",
        "industry": "Developer Tools",
        "size": "51-200 employees",
        "description": "Linear builds modern project management and issue tracking software designed for high-performance software teams, emphasizing speed and streamlined workflows.",
        "linkedin_url": "https://linkedin.com/company/linear-app",
    },
    "notion": {
        "name": "Notion",
        "domain": "notion.so",
        "industry": "Productivity Software",
        "size": "501-1000 employees",
        "description": "Notion offers an all-in-one workspace for notes, docs, wikis, and project management, used by teams of all sizes to collaborate and organize knowledge.",
        "linkedin_url": "https://linkedin.com/company/notionhq",
    },
    "anthropic": {
        "name": "Anthropic",
        "domain": "anthropic.com",
        "industry": "Artificial Intelligence",
        "size": "1001-5000 employees",
        "description": "Anthropic is an AI safety company building reliable, interpretable, and steerable AI systems. Creators of the Claude family of large language models.",
        "linkedin_url": "https://linkedin.com/company/anthropic-ai",
    },
    "stripe": {
        "name": "Stripe",
        "domain": "stripe.com",
        "industry": "FinTech",
        "size": "1001-5000 employees",
        "description": "Stripe builds economic infrastructure for the internet, offering payment processing APIs and tools that enable businesses of all sizes to accept payments and manage revenue online.",
        "linkedin_url": "https://linkedin.com/company/stripe",
    },
}


class MockConnector:
    """
    Returns fixture data. Always works without credentials.
    Use CONNECTOR_MODE=mock (default) for local dev and testing.
    """

    async def search_company(self, company_name: str) -> dict:
        # Return a curated fixture if the company is well-known.
        key = company_name.strip().lower()
        if key in _KNOWN_COMPANIES:
            return _KNOWN_COMPANIES[key]

        # Fall back to deterministic generated data for any other name.
        industry = _pick(company_name, _INDUSTRIES)
        size = _pick(company_name + "_size", _SIZES)
        desc = _pick(company_name + "_desc", _DESCRIPTIONS)

        return {
            "name": company_name,
            "domain": f"{company_name.lower().replace(' ', '')}.com",
            "industry": industry,
            "size": size,
            "description": f"{company_name} {desc}.",
            "linkedin_url": f"https://linkedin.com/company/{company_name.lower().replace(' ', '-')}",
        }

    async def create_note(self, company_id: str, note_body: str) -> str:
        logger.info("Mock: would create HubSpot note for company_id %r", company_id)
        return "mock-note-id-12345"

    async def get_recent_news(self, company_name: str) -> list[str]:
        template_set = _pick(company_name + "_news", _NEWS_TEMPLATES)
        fmt = {
            "name": company_name,
            "amount": _pick(company_name + "_amt", _AMOUNTS),
            "round": _pick(company_name + "_rnd", _ROUNDS),
            "partner": _pick(company_name + "_ptr", _PARTNERS),
            "list_name": _pick(company_name + "_lst", _LISTS),
            "city": _pick(company_name + "_cty", _CITIES),
            "big_co": _pick(company_name + "_bc", _BIG_COS),
            "users": _pick(company_name + "_usr", _USER_COUNTS),
        }
        return [t.format(**fmt) for t in template_set]
