"""Pydantic schemas for extracted and company-mapped controls."""

from __future__ import annotations

from typing import List, Optional, Union

from pydantic import Field, field_validator

from schemas.common import SchemaModel


PageValue = Optional[Union[int, str]]


class Control(SchemaModel):
    """Canonical control object used across extraction, registry, and gap analysis."""

    control_id: str = ""
    doc_id: str = ""
    doc_title: str = ""
    page: PageValue = ""
    clause: str = ""
    type: str = ""
    topic: str = ""
    statement: str = ""
    category: str = ""
    control_type: str = ""
    severity: str = ""
    policy_tags: List[str] = Field(default_factory=list)
    implementation_hint: str = ""
    evidence_type: str = ""
    automation_possible: str = ""
    company_name: str = ""
    sector: str = ""
    business_type: str = ""
    applicability: str = ""
    applicability_reason: str = ""
    owner: str = ""
    status: str = ""
    evidence_link: str = ""
    last_review_date: str = ""
    next_review_date: str = ""
    source_doc_title: str = ""
    source_page: PageValue = ""

    @field_validator("policy_tags", mode="before")
    @classmethod
    def normalize_policy_tags(cls, value):
        """Accept either a list or a single tag-like value."""
        if value is None or value == "":
            return []
        if isinstance(value, list):
            return [str(item).strip() for item in value if str(item).strip()]
        return [str(value).strip()]
