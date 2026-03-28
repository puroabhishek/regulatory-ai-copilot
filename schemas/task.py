"""Pydantic schemas for remediation or implementation tasks."""

from __future__ import annotations

from schemas.common import SchemaModel


class Task(SchemaModel):
    """Action item created from a gap, readiness review, or implementation plan."""

    task_id: str = ""
    title: str = ""
    description: str = ""
    owner: str = ""
    status: str = ""
    priority: str = ""
    due_date: str = ""
    related_control_id: str = ""
    related_gap_id: str = ""
    notes: str = ""
