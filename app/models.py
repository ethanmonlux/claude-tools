from __future__ import annotations

from typing import Literal
from pydantic import BaseModel, field_validator


def _validate_company_name(v: str) -> str:
    v = v.strip()
    if not v:
        raise ValueError("company_name cannot be blank")
    if len(v) > 200:
        raise ValueError("company_name too long")
    return v


# -- Input --


class ResearchRequest(BaseModel):
    company_name: str
    notes: str = (
        ""  # Optional context from the user (e.g. "focus on their AI initiatives")
    )

    @field_validator("company_name")
    @classmethod
    def validate_company_name(cls, v: str) -> str:
        return _validate_company_name(v)


# -- Output --


class ProspectSummary(BaseModel):
    company_name: str
    industry: str
    estimated_size: str  # e.g. "50-200 employees"
    what_they_do: str  # 2-3 sentence plain-English description
    likely_pain_points: list[str]
    why_fits: str  # Why this company would benefit from targeted outreach
    suggested_subject_line: str  # Ready-to-use email subject
    confidence: Literal["high", "medium", "low"]


class ResearchResponse(BaseModel):
    status: Literal["ok", "error", "degraded"]
    ai_generated: bool = True
    data: ProspectSummary | None = None
    error: str | None = None
    crm_note_id: str | None = None


# -- Proposal Generator --


class ProposalData(BaseModel):
    pitch_email_body: str
    recommended_approach: list[str]
    talking_points: list[str]
    follow_up_hook: str


class ProposalRequest(BaseModel):
    company_name: str
    prospect_data: ProspectSummary

    @field_validator("company_name")
    @classmethod
    def validate_company_name(cls, v: str) -> str:
        return _validate_company_name(v)


class ProposalResponse(BaseModel):
    status: Literal["ok", "error", "degraded"]
    ai_generated: bool = True
    data: ProposalData | None = None
    error: str | None = None
