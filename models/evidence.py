"""Database model for evidence references and uploaded artifacts."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, Dict, Optional

from sqlalchemy import ForeignKey, JSON, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from services.db.base import Base, TimestampMixin, UUIDPrimaryKeyMixin

if TYPE_CHECKING:
    from models.control import Control
    from models.organization import Organization, User
    from models.policy import Policy


class EvidenceItem(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """Persisted evidence object linked to a policy, control, or review."""

    __tablename__ = "evidence_items"

    organization_id: Mapped[Optional[str]] = mapped_column(ForeignKey("organizations.id"), nullable=True, index=True)
    policy_id: Mapped[Optional[str]] = mapped_column(ForeignKey("policies.id"), nullable=True, index=True)
    control_id: Mapped[Optional[str]] = mapped_column(ForeignKey("controls.id"), nullable=True, index=True)
    uploaded_by_user_id: Mapped[Optional[str]] = mapped_column(ForeignKey("users.id"), nullable=True, index=True)
    evidence_id: Mapped[Optional[str]] = mapped_column(String(255), nullable=True, index=True)
    evidence_type: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    name: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    reference: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    evidence_link: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    storage_uri: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    source_name: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    owner: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    status: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    details: Mapped[Optional[Dict[str, Any]]] = mapped_column(JSON, nullable=True)

    organization: Mapped[Optional["Organization"]] = relationship(back_populates="evidence_items")
    policy: Mapped[Optional["Policy"]] = relationship(back_populates="evidence_items")
    control: Mapped[Optional["Control"]] = relationship(back_populates="evidence_items")
    uploaded_by_user: Mapped[Optional["User"]] = relationship(back_populates="uploaded_evidence")
