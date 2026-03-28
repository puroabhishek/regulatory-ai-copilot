"""Bootstrap orchestration helpers for evidence-oriented workflows.

The app does not yet have a dedicated evidence page, but these helpers give us
one consistent place to normalize evidence-related data as the feature grows.
"""

from __future__ import annotations

from typing import Any, Iterable, List

from schemas.common import ensure_schema_list
from schemas.control import Control
from schemas.evidence import EvidenceItem


def normalize_evidence_items(items: Iterable[Any]) -> List[dict]:
    """Coerce mixed evidence inputs into the shared schema shape."""

    return [item.to_dict() for item in ensure_schema_list(items, EvidenceItem)]


def build_evidence_register_from_controls(company_controls: Iterable[Any]) -> List[dict]:
    """Create lightweight evidence placeholders from company control inventory rows."""

    evidence_rows: List[dict] = []
    for control in ensure_schema_list(company_controls, Control):
        evidence_rows.append(
            EvidenceItem(
                evidence_id=f"evidence_{control.control_id}" if control.control_id else "",
                control_id=control.control_id,
                evidence_type=control.evidence_type,
                evidence_link=control.evidence_link,
                owner=control.owner,
                status=control.status,
                source_name=control.source_doc_title or control.doc_title,
            ).to_dict()
        )
    return evidence_rows
