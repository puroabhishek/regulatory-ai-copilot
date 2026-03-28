"""Aggregation helpers for multi-dimension gap results.

This module turns dimension-level analysis outputs into the row structure used
by the app, exports, and compatibility wrappers.
"""

from typing import Any, Dict, List

from schemas.common import ensure_schema
from schemas.control import Control
from schemas.gap import (
    EvidenceSufficiencyAssessment,
    GapAssessment,
    ImplementationAssessment,
    PolicyCoverageAssessment,
)


VALID_SUMMARY_STATUSES = {
    "covered": "covered",
    "partially covered": "partially_covered",
    "partially_covered": "partially_covered",
    "partial": "partially_covered",
    "missing": "missing",
}


def safe_gap_text(value: Any) -> str:
    """Normalize a value for display and export."""
    return str(value or "").strip()


def build_gap_base_row(control: Any) -> GapAssessment:
    """Build the shared row fields for a gap result."""
    control_model = ensure_schema(control, Control)
    return GapAssessment(
        control_id=control_model.control_id,
        statement=control_model.statement,
        category=control_model.category,
        severity=control_model.severity,
        source_doc_title=control_model.doc_title or control_model.source_doc_title,
        source_page=control_model.page or control_model.source_page,
    )


def aggregate_gap_result(
    control: Any,
    policy_coverage: Any,
    implementation: Any,
    evidence_sufficiency: Any,
) -> GapAssessment:
    """Combine dimension-specific outputs into one backward-compatible row."""
    row = build_gap_base_row(control)
    policy_coverage_model = ensure_schema(policy_coverage, PolicyCoverageAssessment)
    implementation_model = ensure_schema(implementation, ImplementationAssessment)
    evidence_model = ensure_schema(evidence_sufficiency, EvidenceSufficiencyAssessment)

    return row.model_copy(
        update={
            "status": safe_gap_text(policy_coverage_model.status) or "Missing",
            "reason": safe_gap_text(policy_coverage_model.reason),
            "remediation": safe_gap_text(policy_coverage_model.remediation),
            "policy_coverage_status": safe_gap_text(policy_coverage_model.status),
            "policy_coverage_reason": safe_gap_text(policy_coverage_model.reason),
            "policy_coverage_remediation": safe_gap_text(policy_coverage_model.remediation),
            "implementation_status": safe_gap_text(implementation_model.status),
            "implementation_reason": safe_gap_text(implementation_model.reason),
            "implementation_remediation": safe_gap_text(implementation_model.remediation),
            "evidence_sufficiency_status": safe_gap_text(evidence_model.status),
            "evidence_sufficiency_reason": safe_gap_text(evidence_model.reason),
            "evidence_sufficiency_remediation": safe_gap_text(evidence_model.remediation),
            "owner": safe_gap_text(implementation_model.owner),
            "applicability": safe_gap_text(implementation_model.applicability),
            "evidence_type": safe_gap_text(evidence_model.evidence_type),
            "evidence_link": safe_gap_text(evidence_model.evidence_link),
        }
    )


def build_error_gap_result(control: Any, error: Exception) -> GapAssessment:
    """Build a consistent error row when one control fails analysis."""
    row = build_gap_base_row(control)
    error_text = f"{type(error).__name__}: {str(error)}"
    return row.model_copy(
        update={
            "status": "Error",
            "reason": error_text,
            "remediation": "",
            "policy_coverage_status": "Error",
            "policy_coverage_reason": error_text,
            "policy_coverage_remediation": "",
            "implementation_status": "Not Assessed",
            "implementation_reason": "Implementation analysis was skipped because policy coverage failed.",
            "implementation_remediation": "",
            "evidence_sufficiency_status": "Not Assessed",
            "evidence_sufficiency_reason": "Evidence analysis was skipped because policy coverage failed.",
            "evidence_sufficiency_remediation": "",
            "owner": "",
            "applicability": "",
            "evidence_type": "",
            "evidence_link": "",
        }
    )


def summarize_gap_results(rows: List[Any]) -> Dict[str, Any]:
    """Summarize the primary gap status across analyzed controls."""
    summary = {
        "total_reviewed": len(rows),
        "total_controls": len(rows),
        "covered": 0,
        "partially_covered": 0,
        "missing": 0,
        "errors": 0,
    }

    for row in rows:
        row_model = ensure_schema(row, GapAssessment)
        status = VALID_SUMMARY_STATUSES.get(safe_gap_text(row_model.status).lower())
        if status == "covered":
            summary["covered"] += 1
        elif status == "partially_covered":
            summary["partially_covered"] += 1
        elif status == "missing":
            summary["missing"] += 1
        else:
            summary["errors"] += 1

    return summary
