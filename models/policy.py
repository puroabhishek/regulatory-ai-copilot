"""Database model for policy drafts, generated policy content, and metadata."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, Dict, List, Optional

from sqlalchemy import ForeignKey, JSON, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from services.db.base import Base, TimestampMixin, UUIDPrimaryKeyMixin

if TYPE_CHECKING:
    from models.control import Control
    from models.evidence import EvidenceItem
    from models.gap import GapAssessment
    from models.organization import Organization, OrganizationProfile, User
    from models.readiness import AuditReadiness
    from models.task import Task


class Policy(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """Persisted policy draft or generated policy artifact."""

    __tablename__ = "policies"

    organization_id: Mapped[Optional[str]] = mapped_column(ForeignKey("organizations.id"), nullable=True, index=True)
    organization_profile_id: Mapped[Optional[str]] = mapped_column(
        ForeignKey("organization_profiles.id"),
        nullable=True,
        index=True,
    )
    owner_user_id: Mapped[Optional[str]] = mapped_column(ForeignKey("users.id"), nullable=True, index=True)
    policy_name: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    title: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    version: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    status: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    objective: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    policy_text: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    scope: Mapped[Optional[List[str]]] = mapped_column(JSON, nullable=True)
    definitions: Mapped[Optional[List[Dict[str, Any]]]] = mapped_column(JSON, nullable=True)
    responsibilities: Mapped[Optional[List[Dict[str, Any]]]] = mapped_column(JSON, nullable=True)
    policy_statements: Mapped[Optional[List[Dict[str, Any]]]] = mapped_column(JSON, nullable=True)
    procedures: Mapped[Optional[List[str]]] = mapped_column(JSON, nullable=True)
    records: Mapped[Optional[List[str]]] = mapped_column(JSON, nullable=True)
    exceptions: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    review_cycle: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    drafting_instructions: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    selected_control_files: Mapped[Optional[List[str]]] = mapped_column(JSON, nullable=True)
    selected_profile_file: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    profile_summary: Mapped[Optional[Dict[str, Any]]] = mapped_column(JSON, nullable=True)
    sample_policy_text: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    style_reference_excerpt: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    source_context: Mapped[Optional[Dict[str, Any]]] = mapped_column(JSON, nullable=True)

    organization: Mapped[Optional["Organization"]] = relationship(back_populates="policies")
    organization_profile: Mapped[Optional["OrganizationProfile"]] = relationship()
    owner_user: Mapped[Optional["User"]] = relationship(back_populates="owned_policies")
    controls: Mapped[List["Control"]] = relationship(back_populates="policy")
    evidence_items: Mapped[List["EvidenceItem"]] = relationship(back_populates="policy")
    gap_assessments: Mapped[List["GapAssessment"]] = relationship(back_populates="policy")
    readiness_records: Mapped[List["AuditReadiness"]] = relationship(back_populates="policy")
    tasks: Mapped[List["Task"]] = relationship(back_populates="policy")
