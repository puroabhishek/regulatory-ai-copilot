"""Bootstrap orchestration helpers for readiness-oriented workflows."""

from __future__ import annotations

from typing import Any, Iterable, List

from domain.gaps.aggregator import summarize_gap_results
from schemas.common import ensure_schema_list
from schemas.evidence import EvidenceItem
from schemas.gap import GapAssessment
from schemas.readiness import AuditReadiness


def build_readiness_snapshot(
    area: str,
    gap_rows: Iterable[Any],
    evidence_items: Iterable[Any] | None = None,
    owner: str = "",
    notes: str = "",
) -> dict:
    """Build a simple readiness summary from gap results and supporting evidence."""

    gap_models = ensure_schema_list(gap_rows, GapAssessment)
    evidence_models = ensure_schema_list(evidence_items or [], EvidenceItem)
    summary = summarize_gap_results(gap_models)

    total = summary.get("total_controls", 0)
    covered = summary.get("covered", 0)
    partial = summary.get("partially_covered", 0)
    missing = summary.get("missing", 0)

    score = round(((covered + (0.5 * partial)) / total) * 100, 1) if total else 0.0
    if missing:
        status = "Needs Attention"
    elif partial:
        status = "In Progress"
    else:
        status = "Ready"

    readiness = AuditReadiness(
        area=area,
        status=status,
        score=score,
        notes=notes,
        owner=owner,
        evidence_items=evidence_models,
        open_gap_ids=[row.control_id for row in gap_models if row.status and row.status != "Covered"],
        recommended_actions=[row.remediation for row in gap_models if row.remediation][:10],
    )

    return {
        "readiness": readiness.to_dict(),
        "summary": summary,
    }
