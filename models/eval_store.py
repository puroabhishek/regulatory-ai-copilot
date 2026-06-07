from __future__ import annotations
from typing import Any, Dict, Optional
from sqlalchemy import Boolean, Float, ForeignKey, Integer, JSON, String, Text, false
from sqlalchemy.orm import Mapped, mapped_column
from services.db.base import Base, TimestampMixin, UUIDPrimaryKeyMixin


class EvalCase(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "eval_cases"

    task: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    name: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    input_data: Mapped[Optional[Dict[str, Any]]] = mapped_column(JSON, nullable=True)
    expected_output: Mapped[Optional[Dict[str, Any]]] = mapped_column(JSON, nullable=True)
    source: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)  # manual|excel_import|qcb_feedback
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    created_by_user_id: Mapped[Optional[str]] = mapped_column(ForeignKey("users.id"), nullable=True)


class EvalRun(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "eval_runs"

    task: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    model_used: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    prompt_hash: Mapped[Optional[str]] = mapped_column(String(16), nullable=True)
    total_cases: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    passed: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    failed: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    errored: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    pass_rate_pct: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    pass_threshold: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    triggered_by_user_id: Mapped[Optional[str]] = mapped_column(ForeignKey("users.id"), nullable=True)


class EvalResult(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "eval_results"

    eval_run_id: Mapped[str] = mapped_column(ForeignKey("eval_runs.id"), nullable=False, index=True)
    eval_case_id: Mapped[str] = mapped_column(ForeignKey("eval_cases.id"), nullable=False, index=True)
    raw_output: Mapped[Optional[Dict[str, Any]]] = mapped_column(JSON, nullable=True)
    scores: Mapped[Optional[Dict[str, Any]]] = mapped_column(JSON, nullable=True)
    passed: Mapped[bool] = mapped_column(Boolean, nullable=False, default=false())
    error: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
