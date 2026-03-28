"""Database model for remediation, implementation, and follow-up tasks."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, Dict, Optional

from sqlalchemy import ForeignKey, JSON, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from services.db.base import Base, TimestampMixin, UUIDPrimaryKeyMixin

if TYPE_CHECKING:
    from models.control import Control
    from models.gap import GapAssessment
    from models.organization import Organization, User
    from models.policy import Policy


class Task(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """Action item tracked against a policy, control, or gap assessment."""

    __tablename__ = "tasks"

    organization_id: Mapped[Optional[str]] = mapped_column(ForeignKey("organizations.id"), nullable=True, index=True)
    policy_id: Mapped[Optional[str]] = mapped_column(ForeignKey("policies.id"), nullable=True, index=True)
    control_id: Mapped[Optional[str]] = mapped_column(ForeignKey("controls.id"), nullable=True, index=True)
    gap_assessment_id: Mapped[Optional[str]] = mapped_column(
        ForeignKey("gap_assessments.id"),
        nullable=True,
        index=True,
    )
    assigned_user_id: Mapped[Optional[str]] = mapped_column(ForeignKey("users.id"), nullable=True, index=True)
    task_id: Mapped[Optional[str]] = mapped_column(String(255), nullable=True, index=True)
    title: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    owner: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    status: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    priority: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    due_date: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    related_control_id: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    related_gap_id: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    details: Mapped[Optional[Dict[str, Any]]] = mapped_column(JSON, nullable=True)

    organization: Mapped[Optional["Organization"]] = relationship(back_populates="tasks")
    policy: Mapped[Optional["Policy"]] = relationship(back_populates="tasks")
    control: Mapped[Optional["Control"]] = relationship(back_populates="tasks")
    gap_assessment: Mapped[Optional["GapAssessment"]] = relationship(back_populates="tasks")
    assigned_user: Mapped[Optional["User"]] = relationship(back_populates="assigned_tasks")
