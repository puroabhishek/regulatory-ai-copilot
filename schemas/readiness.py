"""Pydantic schemas for audit or compliance readiness snapshots."""

from __future__ import annotations

from typing import List

from pydantic import Field

from schemas.common import SchemaModel
from schemas.evidence import EvidenceItem


class AuditReadiness(SchemaModel):
    """Summary of readiness for an audit domain or review area."""

    area: str = ""
    status: str = ""
    score: float = 0.0
    notes: str = ""
    owner: str = ""
    evidence_items: List[EvidenceItem] = Field(default_factory=list)
    open_gap_ids: List[str] = Field(default_factory=list)
    recommended_actions: List[str] = Field(default_factory=list)
