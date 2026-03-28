"""Database model for audit or compliance readiness snapshots."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, Dict, Optional

from sqlalchemy import Float, ForeignKey, JSON, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from services.db.base import Base, TimestampMixin, UUIDPrimaryKeyMixin

if TYPE_CHECKING:
    from models.organization import Organization
    from models.policy import Policy


class AuditReadiness(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """Readiness snapshot for an audit domain, control family, or review area."""

    __tablename__ = "audit_readiness"

    organization_id: Mapped[Optional[str]] = mapped_column(ForeignKey("organizations.id"), nullable=True, index=True)
    policy_id: Mapped[Optional[str]] = mapped_column(ForeignKey("policies.id"), nullable=True, index=True)
    area: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    status: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    score: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    owner: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    evidence_items: Mapped[Optional[list[Dict[str, Any]]]] = mapped_column(JSON, nullable=True)
    open_gap_ids: Mapped[Optional[list[str]]] = mapped_column(JSON, nullable=True)
    recommended_actions: Mapped[Optional[list[str]]] = mapped_column(JSON, nullable=True)
    details: Mapped[Optional[Dict[str, Any]]] = mapped_column(JSON, nullable=True)

    organization: Mapped[Optional["Organization"]] = relationship(back_populates="readiness_records")
    policy: Mapped[Optional["Policy"]] = relationship(back_populates="readiness_records")
