from __future__ import annotations
from typing import Any, Dict, Optional
from sqlalchemy import ForeignKey, Integer, JSON, String, Text
from sqlalchemy.orm import Mapped, mapped_column
from services.db.base import Base, TimestampMixin, UUIDPrimaryKeyMixin


class AuditLog(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "audit_logs"

    org_id: Mapped[Optional[str]] = mapped_column(ForeignKey("organizations.id"), nullable=True, index=True)
    user_id: Mapped[Optional[str]] = mapped_column(ForeignKey("users.id"), nullable=True, index=True)
    action: Mapped[Optional[str]] = mapped_column(String(100), nullable=True, index=True)
    entity_type: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    entity_id: Mapped[Optional[str]] = mapped_column(String(36), nullable=True)
    model_used: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    prompt_hash: Mapped[Optional[str]] = mapped_column(String(16), nullable=True)
    duration_ms: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    input_summary: Mapped[Optional[Dict[str, Any]]] = mapped_column(JSON, nullable=True)
    result_summary: Mapped[Optional[Dict[str, Any]]] = mapped_column(JSON, nullable=True)
    error: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
