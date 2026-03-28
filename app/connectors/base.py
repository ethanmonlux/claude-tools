from __future__ import annotations

from typing import Protocol


class ResearchConnector(Protocol):
    """
    Abstracts external data sources used by the prospect research skill.
    All skill logic depends on this protocol, never on a concrete implementation.
    This makes the system testable without live credentials (use MockConnector).
    """

    async def search_company(self, company_name: str) -> dict:
        """
        Return basic company info: name, domain, industry, size, description.
        Shape: { name, domain, industry, size, description, linkedin_url }
        Returns empty dict if not found.
        """
        ...

    async def get_recent_news(self, company_name: str) -> list[str]:
        """
        Return a list of recent news headlines or summaries about the company.
        Returns empty list if none found.
        """
        ...

    async def create_note(self, company_id: str, note_body: str) -> str:
        """
        Create a note in the CRM attached to the company record.
        Accepts the company_id from a prior search_company call.
        Returns the note ID on success, empty string on failure.
        """
        ...
