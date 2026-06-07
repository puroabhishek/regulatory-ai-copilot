from __future__ import annotations
from typing import Optional
from sqlalchemy import Boolean, ForeignKey, String, Text, false
from sqlalchemy.orm import Mapped, mapped_column
from services.db.base import Base, TimestampMixin, UUIDPrimaryKeyMixin


class PolicyVersion(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """QCB-reviewed / approved policy library used as style references and eval ground truth."""
    __tablename__ = "policy_versions"

    org_id: Mapped[Optional[str]] = mapped_column(ForeignKey("organizations.id"), nullable=True, index=True)
    policy_name: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    version_label: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    source_regulation: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    policy_text: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    file_path: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    qcb_status: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)  # pending|approved|rejected|partial
    qcb_feedback_notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    qcb_feedback_date: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    is_reference_policy: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False, server_default=false())
    uploaded_by_user_id: Mapped[Optional[str]] = mapped_column(ForeignKey("users.id"), nullable=True)
