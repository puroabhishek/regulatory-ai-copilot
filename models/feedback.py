from __future__ import annotations
from typing import Optional
from sqlalchemy import ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column
from services.db.base import Base, TimestampMixin, UUIDPrimaryKeyMixin


class OutputFeedback(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "output_feedback"

    org_id: Mapped[Optional[str]] = mapped_column(ForeignKey("organizations.id"), nullable=True, index=True)
    user_id: Mapped[Optional[str]] = mapped_column(ForeignKey("users.id"), nullable=True, index=True)
    output_type: Mapped[Optional[str]] = mapped_column(String(50), nullable=True, index=True)  # policy|gap_analysis
    output_ref_id: Mapped[Optional[str]] = mapped_column(String(36), nullable=True)
    rating: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)  # positive|negative
    reason_code: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    reason_text: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    model_used: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    prompt_hash: Mapped[Optional[str]] = mapped_column(String(16), nullable=True)
