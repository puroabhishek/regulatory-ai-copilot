"""Implementation-dimension heuristics for gap assessments.

This module derives an implementation status from the company control registry
so orchestration and UI code do not need to reason about owner, applicability,
or current implementation state directly.
"""

from typing import Any, Optional

from schemas.common import ensure_schema
from schemas.control import Control
from schemas.gap import ImplementationAssessment


VALID_IMPLEMENTATION_STATUSES = {
    "implemented": "Implemented",
    "in progress": "In Progress",
    "not assessed": "Not Assessed",
    "not applicable": "Not Applicable",
}


def _safe_text(value: Any) -> str:
    return str(value or "").strip()


def normalize_implementation_status(value: Any) -> str:
    """Normalize company-control implementation labels."""
    text = _safe_text(value).lower()
    return VALID_IMPLEMENTATION_STATUSES.get(text, "Not Assessed")


def analyze_implementation_gap(
    control: Any,
    company_control: Optional[Any] = None,
) -> ImplementationAssessment:
    """Summarize the implementation state for a control in company context."""
    ensure_schema(control, Control)
    company_control_model = ensure_schema(company_control or {}, Control)

    status = normalize_implementation_status(company_control_model.status)
    owner = _safe_text(company_control_model.owner)
    applicability = _safe_text(company_control_model.applicability) or "Applicable"
    applicability_reason = _safe_text(company_control_model.applicability_reason)

    if status == "Implemented":
        reason = "Company control inventory marks this control as implemented."
        remediation = ""
    elif status == "In Progress":
        reason = "Company control inventory marks this control as in progress."
        remediation = "Complete the implementation work and confirm operating ownership."
    elif status == "Not Applicable":
        reason = applicability_reason or "Company control inventory marks this control as not applicable."
        remediation = ""
    else:
        reason = "No implementation assessment is recorded yet in the company control inventory."
        remediation = "Assign an owner and record the implementation status for this control."

    if owner:
        reason = f"{reason} Owner: {owner}."

    return ImplementationAssessment(
        status=status,
        reason=reason,
        remediation=remediation,
        owner=owner,
        applicability=applicability,
    )
