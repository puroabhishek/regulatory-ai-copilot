from __future__ import annotations
from typing import Optional
from sqlalchemy import ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column
from services.db.base import Base, TimestampMixin, UUIDPrimaryKeyMixin


class AppSetting(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """Company-level configuration controlled via admin portal."""
    __tablename__ = "app_settings"

    key: Mapped[str] = mapped_column(String(255), nullable=False, unique=True, index=True)
    value: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    updated_by_user_id: Mapped[Optional[str]] = mapped_column(ForeignKey("users.id"), nullable=True)
