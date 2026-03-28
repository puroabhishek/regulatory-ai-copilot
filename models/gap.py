"""Database model for aggregated gap assessment results."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, Dict, Optional

from sqlalchemy import ForeignKey, JSON, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from services.db.base import Base, TimestampMixin, UUIDPrimaryKeyMixin

if TYPE_CHECKING:
    from models.control import Control
    from models.organization import Organization
    from models.policy import Policy
    from models.task import Task


class GapAssessment(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """Persisted gap row spanning policy, implementation, and evidence dimensions."""

    __tablename__ = "gap_assessments"

    organization_id: Mapped[Optional[str]] = mapped_column(ForeignKey("organizations.id"), nullable=True, index=True)
    policy_id: Mapped[Optional[str]] = mapped_column(ForeignKey("policies.id"), nullable=True, index=True)
    control_id: Mapped[Optional[str]] = mapped_column(ForeignKey("controls.id"), nullable=True, index=True)
    control_reference: Mapped[Optional[str]] = mapped_column(String(255), nullable=True, index=True)
    statement: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    category: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    source_doc_title: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    source_page: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    status: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    severity: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    reason: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    remediation: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    policy_coverage_status: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    policy_coverage_reason: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    policy_coverage_remediation: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    implementation_status: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    implementation_reason: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    implementation_remediation: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    evidence_sufficiency_status: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    evidence_sufficiency_reason: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    evidence_sufficiency_remediation: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    owner: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    applicability: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    evidence_type: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    evidence_link: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    details: Mapped[Optional[Dict[str, Any]]] = mapped_column(JSON, nullable=True)

    organization: Mapped[Optional["Organization"]] = relationship(back_populates="gap_assessments")
    policy: Mapped[Optional["Policy"]] = relationship(back_populates="gap_assessments")
    control: Mapped[Optional["Control"]] = relationship(back_populates="gap_assessments")
    tasks: Mapped[list["Task"]] = relationship(back_populates="gap_assessment")
