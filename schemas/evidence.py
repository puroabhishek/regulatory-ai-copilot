"""Pydantic schemas for evidence artifacts and references."""

from __future__ import annotations

from schemas.common import SchemaModel


class EvidenceItem(SchemaModel):
    """Evidence reference associated with a control or readiness review."""

    evidence_id: str = ""
    control_id: str = ""
    evidence_type: str = ""
    reference: str = ""
    evidence_link: str = ""
    description: str = ""
    owner: str = ""
    status: str = ""
    notes: str = ""
    source_name: str = ""
