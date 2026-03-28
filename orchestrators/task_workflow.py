"""Bootstrap orchestration helpers for remediation task flows."""

from __future__ import annotations

import time
from typing import Any, Iterable, List

from schemas.common import ensure_schema, ensure_schema_list
from schemas.gap import GapAssessment
from schemas.task import Task


def normalize_tasks(tasks: Iterable[Any]) -> List[dict]:
    """Coerce mixed task inputs into the shared task schema."""

    return [task.to_dict() for task in ensure_schema_list(tasks, Task)]


def create_task_from_gap(
    gap_row: Any,
    owner: str = "",
    priority: str = "Medium",
    due_date: str = "",
) -> dict:
    """Build a simple remediation task from an existing gap row."""

    gap = ensure_schema(gap_row, GapAssessment)
    task = Task(
        task_id=f"task_{gap.control_id}_{int(time.time())}" if gap.control_id else f"task_{int(time.time())}",
        title=f"Remediate {gap.control_id or 'gap item'}",
        description=gap.remediation or gap.reason,
        owner=owner or gap.owner,
        status="Open",
        priority=priority,
        due_date=due_date,
        related_control_id=gap.control_id,
        related_gap_id=gap.control_id,
        notes=gap.reason,
    )
    return task.to_dict()
