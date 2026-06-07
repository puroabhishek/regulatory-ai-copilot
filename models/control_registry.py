from __future__ import annotations
from typing import Any, Dict, List, Optional
from sqlalchemy import Boolean, ForeignKey, JSON, String, Text, true
from sqlalchemy.orm import Mapped, mapped_column
from services.db.base import Base, TimestampMixin, UUIDPrimaryKeyMixin


class RegistryControl(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """Central MECE control registry — country × sector × activity × controls."""
    __tablename__ = "registry_controls"

    # Taxonomy dimensions
    country: Mapped[Optional[str]] = mapped_column(String(100), nullable=True, index=True)
    sector: Mapped[Optional[str]] = mapped_column(String(100), nullable=True, index=True)
    sub_sector: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    activity: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    business_model: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)

    # Regulation metadata
    regulation_name: Mapped[Optional[str]] = mapped_column(String(255), nullable=True, index=True)
    regulation_version: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    issuing_body: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    clause_reference: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    source_doc_title: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)

    # Control content
    control_code: Mapped[Optional[str]] = mapped_column(String(255), nullable=True, index=True, unique=True)
    control_statement: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    control_type: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    severity: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    category: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    policy_tags: Mapped[Optional[List[str]]] = mapped_column(JSON, nullable=True)
    implementation_hint: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Status
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True, server_default=true())
    superseded_by_id: Mapped[Optional[str]] = mapped_column(ForeignKey("registry_controls.id"), nullable=True)
    created_by_user_id: Mapped[Optional[str]] = mapped_column(ForeignKey("users.id"), nullable=True)
    ingestion_source: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)  # "pdf" | "csv" | "manual"
    extra_data: Mapped[Optional[Dict[str, Any]]] = mapped_column(JSON, nullable=True)
