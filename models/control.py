"""Database model for canonical controls and company-mapped control records."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, Dict, List, Optional

from sqlalchemy import ForeignKey, Integer, JSON, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from services.db.base import Base, TimestampMixin, UUIDPrimaryKeyMixin

if TYPE_CHECKING:
    from models.evidence import EvidenceItem
    from models.gap import GapAssessment
    from models.organization import Organization
    from models.policy import Policy
    from models.task import Task


class Control(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """Persisted control extracted from regulations or mapped to an organization."""

    __tablename__ = "controls"

    organization_id: Mapped[Optional[str]] = mapped_column(ForeignKey("organizations.id"), nullable=True, index=True)
    policy_id: Mapped[Optional[str]] = mapped_column(ForeignKey("policies.id"), nullable=True, index=True)
    control_id: Mapped[Optional[str]] = mapped_column(String(255), nullable=True, index=True)
    doc_id: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    doc_title: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    source_doc_title: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    page: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    source_page: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    clause: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    type: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    topic: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    statement: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    category: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    control_type: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    severity: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    policy_tags: Mapped[Optional[List[str]]] = mapped_column(JSON, nullable=True)
    implementation_hint: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    evidence_type: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    automation_possible: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    company_name: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    sector: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    business_type: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    applicability: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    applicability_reason: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    owner: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    status: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    evidence_link: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    last_review_date: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    next_review_date: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    extra_data: Mapped[Optional[Dict[str, Any]]] = mapped_column(JSON, nullable=True)

    organization: Mapped[Optional["Organization"]] = relationship(back_populates="controls")
    policy: Mapped[Optional["Policy"]] = relationship(back_populates="controls")
    evidence_items: Mapped[List["EvidenceItem"]] = relationship(back_populates="control")
    gap_assessments: Mapped[List["GapAssessment"]] = relationship(back_populates="control")
    tasks: Mapped[List["Task"]] = relationship(back_populates="control")
