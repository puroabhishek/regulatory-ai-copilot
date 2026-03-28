"""Database models for organizations, users, and saved organization profiles.

These models are intentionally permissive so we can start persisting key
objects without forcing a full relational redesign on the existing app.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, Dict, List, Optional

from sqlalchemy import Boolean, ForeignKey, JSON, String, Text, UniqueConstraint, true
from sqlalchemy.orm import Mapped, mapped_column, relationship

from services.db.base import Base, TimestampMixin, UUIDPrimaryKeyMixin

if TYPE_CHECKING:
    from models.control import Control
    from models.evidence import EvidenceItem
    from models.gap import GapAssessment
    from models.policy import Policy
    from models.readiness import AuditReadiness
    from models.task import Task


class Organization(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """Top-level tenant record for the product."""

    __tablename__ = "organizations"

    name: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    slug: Mapped[Optional[str]] = mapped_column(String(255), nullable=True, unique=True)
    legal_name: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    country: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    regulator: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True, server_default=true())
    settings: Mapped[Optional[Dict[str, Any]]] = mapped_column(JSON, nullable=True)

    users: Mapped[List["User"]] = relationship(back_populates="organization", cascade="all, delete-orphan")
    profiles: Mapped[List["OrganizationProfile"]] = relationship(
        back_populates="organization",
        cascade="all, delete-orphan",
    )
    policies: Mapped[List["Policy"]] = relationship(back_populates="organization")
    controls: Mapped[List["Control"]] = relationship(back_populates="organization")
    evidence_items: Mapped[List["EvidenceItem"]] = relationship(back_populates="organization")
    gap_assessments: Mapped[List["GapAssessment"]] = relationship(back_populates="organization")
    readiness_records: Mapped[List["AuditReadiness"]] = relationship(back_populates="organization")
    tasks: Mapped[List["Task"]] = relationship(back_populates="organization")


class User(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """Basic user account model for ownership and assignments."""

    __tablename__ = "users"

    organization_id: Mapped[Optional[str]] = mapped_column(ForeignKey("organizations.id"), nullable=True, index=True)
    email: Mapped[Optional[str]] = mapped_column(String(255), nullable=True, unique=True)
    full_name: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    role: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    password_hash: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True, server_default=true())
    last_login_at: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)

    organization: Mapped[Optional["Organization"]] = relationship(back_populates="users")
    owned_policies: Mapped[List["Policy"]] = relationship(back_populates="owner_user")
    uploaded_evidence: Mapped[List["EvidenceItem"]] = relationship(back_populates="uploaded_by_user")
    assigned_tasks: Mapped[List["Task"]] = relationship(back_populates="assigned_user")


class OrganizationProfile(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """Saved organization/business profile for policy and control generation."""

    __tablename__ = "organization_profiles"
    __table_args__ = (
        UniqueConstraint("organization_id", "profile_name", name="uq_organization_profiles_org_profile_name"),
    )

    organization_id: Mapped[Optional[str]] = mapped_column(ForeignKey("organizations.id"), nullable=True, index=True)
    profile_name: Mapped[str] = mapped_column(String(255), nullable=False)
    country: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    regulator: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    sector: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    business_type: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    business_model: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    target_customers: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    profile_data: Mapped[Optional[Dict[str, Any]]] = mapped_column(JSON, nullable=True)
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True, server_default=true())

    organization: Mapped[Optional["Organization"]] = relationship(back_populates="profiles")
