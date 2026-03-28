"""Evidence-sufficiency heuristics for gap assessments.

This module evaluates whether a mapped company control has enough evidence
metadata to support review. It remains heuristic for now and intentionally
avoids any OCR or document parsing responsibilities.
"""

from typing import Any, Optional

from schemas.common import ensure_schema
from schemas.control import Control
from schemas.gap import EvidenceSufficiencyAssessment


def _safe_text(value: Any) -> str:
    return str(value or "").strip()


def analyze_evidence_sufficiency(
    control: Any,
    company_control: Optional[Any] = None,
) -> EvidenceSufficiencyAssessment:
    """Assess whether the current control record carries enough evidence detail."""
    ensure_schema(control, Control)
    company_control_model = ensure_schema(company_control or {}, Control)

    control_status = _safe_text(company_control_model.status)
    evidence_type = _safe_text(company_control_model.evidence_type) or "Documentary Evidence"
    evidence_link = _safe_text(company_control_model.evidence_link)

    if control_status == "Not Applicable":
        status = "Not Applicable"
        reason = "Evidence is not required because the control is marked as not applicable."
        remediation = ""
    elif evidence_link:
        status = "Sufficient"
        reason = "A concrete evidence reference is already recorded for this control."
        remediation = ""
    elif control_status == "Implemented":
        status = "Partial"
        reason = f"The control is marked implemented, but no evidence reference is recorded. Expected evidence: {evidence_type}."
        remediation = "Attach or reference the supporting evidence artifact for this implemented control."
    else:
        status = "Missing"
        reason = f"No evidence reference is recorded yet. Expected evidence: {evidence_type}."
        remediation = "Capture evidence artifacts or links that demonstrate the control in practice."

    return EvidenceSufficiencyAssessment(
        status=status,
        reason=reason,
        remediation=remediation,
        evidence_type=evidence_type,
        evidence_link=evidence_link,
    )
