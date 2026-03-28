from __future__ import annotations

import logging
import time

import httpx

logger = logging.getLogger(__name__)

_BASE_URL = "https://api.hubapi.com"

# HubSpot property names we request from the Companies API.
_PROPERTIES = [
    "name",
    "domain",
    "industry",
    "numberofemployees",
    "description",
    "linkedin_company_page",
]


class HubSpotConnector:
    """
    Calls the HubSpot CRM API to fetch company data.
    Requires a private-app access token (HUBSPOT_API_KEY).
    """

    def __init__(self, api_key: str) -> None:
        self._api_key = api_key
        self._timeout = 10.0

    def _client_kwargs(self) -> dict:
        return {
            "base_url": _BASE_URL,
            "headers": {"Authorization": f"Bearer {self._api_key}"},
            "timeout": self._timeout,
        }

    async def search_company(self, company_name: str) -> dict:
        """Search HubSpot Companies by name and return normalised info."""
        body = {
            "filterGroups": [
                {
                    "filters": [
                        {
                            "propertyName": "name",
                            "operator": "CONTAINS_TOKEN",
                            "value": company_name,
                        }
                    ]
                }
            ],
            "properties": _PROPERTIES,
            "limit": 1,
        }

        try:
            async with httpx.AsyncClient(**self._client_kwargs()) as client:
                resp = await client.post("/crm/v3/objects/companies/search", json=body)
                resp.raise_for_status()
        except httpx.HTTPError as exc:
            logger.warning("HubSpot search failed for %r: %s", company_name, exc)
            return {}

        results = resp.json().get("results", [])
        if not results:
            return {}

        first = results[0]
        props = first.get("properties", {})
        return {
            "name": props.get("name", ""),
            "domain": props.get("domain", ""),
            "industry": props.get("industry", ""),
            "size": props.get("numberofemployees", ""),
            "description": props.get("description", ""),
            "linkedin_url": props.get("linkedin_company_page", ""),
            "hubspot_id": first.get("id", ""),
        }

    async def get_recent_news(self, company_name: str) -> list[str]:
        # Not yet implemented — returns an empty list.
        # The mock connector (app/connectors/mock.py) returns fixture data for testing.
        return []

    async def create_note(self, company_id: str, note_body: str) -> str:
        """Create a note in HubSpot attached to the company record."""
        if not company_id:
            logger.warning("Empty company_id — cannot create note")
            return ""

        try:
            body = {
                "properties": {
                    "hs_note_body": note_body,
                    "hs_timestamp": str(int(time.time() * 1000)),
                },
                "associations": [
                    {
                        "to": {"id": company_id},
                        "types": [
                            {
                                "associationCategory": "HUBSPOT_DEFINED",
                                "associationTypeId": 190,
                            }
                        ],
                    }
                ],
            }

            async with httpx.AsyncClient(**self._client_kwargs()) as client:
                resp = await client.post("/crm/v3/objects/notes", json=body)
                resp.raise_for_status()
            note_id = resp.json().get("id", "")
            logger.info(
                "Created HubSpot note %s for company_id %s", note_id, company_id
            )
            return note_id
        except Exception as exc:
            logger.warning(
                "Failed to create HubSpot note for company_id %s: %s", company_id, exc
            )
            return ""
