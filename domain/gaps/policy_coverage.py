"""Policy-coverage analysis for the gap engine.

This module evaluates whether policy text covers a given control statement.
It owns prompt construction and response validation, but does not perform any
file I/O or UI rendering.
"""

from typing import Any, Dict, Optional

from services.llm.client import llm_json
from schemas.common import ensure_schema
from schemas.control import Control
from schemas.gap import PolicyCoverageAssessment


VALID_POLICY_COVERAGE_STATUSES = {
    "covered": "Covered",
    "partially covered": "Partially Covered",
    "partially_covered": "Partially Covered",
    "partial": "Partially Covered",
    "missing": "Missing",
}


def safe_gap_text(value: Any) -> str:
    """Return a normalized string for gap-analysis fields."""
    return str(value or "").strip()


def normalize_policy_coverage_status(value: Any) -> str:
    """Normalize model output to the supported policy-coverage labels."""
    text = safe_gap_text(value).lower()
    return VALID_POLICY_COVERAGE_STATUSES.get(text, "")


def build_policy_coverage_prompt(control: Any, policy_text: str) -> str:
    """Build the review prompt used to assess policy coverage for one control."""
    control_model = ensure_schema(control, Control)
    statement = safe_gap_text(control_model.statement)
    control_id = safe_gap_text(control_model.control_id)
    trimmed_policy_text = safe_gap_text(policy_text)[:5000]

    return f"""
You are a compliance reviewer.

Task:
Compare the policy text against the control and decide whether the control is:
- Covered
- Partially Covered
- Missing

Return ONLY valid JSON in this exact format:
{{
  "status": "Covered | Partially Covered | Missing",
  "reason": "short explanation",
  "remediation": "specific suggested addition or fix"
}}

CONTROL ID:
{control_id}

CONTROL:
{statement}

POLICY TEXT:
\"\"\"
{trimmed_policy_text}
\"\"\"

Rules:
1. Be strict and practical.
2. "Covered" only if the policy clearly addresses the control.
3. "Partially Covered" if the policy touches the topic but misses specificity.
4. "Missing" if not addressed.
5. Remediation must be concise and actionable.
"""


def validate_policy_coverage_output(output: Dict[str, Any]) -> PolicyCoverageAssessment:
    """Validate and normalize the structured LLM response."""
    if not isinstance(output, dict):
        raise TypeError(f"llm_json returned {type(output).__name__}, expected dict")

    normalized_status = normalize_policy_coverage_status(output.get("status"))
    if not normalized_status:
        raise ValueError(
            f"Invalid LLM status: {output.get('status')!r}. Expected one of: Covered, Partially Covered, Missing"
        )

    return PolicyCoverageAssessment(
        status=normalized_status,
        reason=safe_gap_text(output.get("reason")),
        remediation=safe_gap_text(output.get("remediation")),
    )


def analyze_policy_coverage(
    control: Any,
    policy_text: str,
    model: Optional[str] = None,
) -> PolicyCoverageAssessment:
    """Assess whether a policy covers the supplied control statement."""
    control_model = ensure_schema(control, Control)
    statement = safe_gap_text(control_model.statement)
    control_id = safe_gap_text(control_model.control_id)

    if not statement:
        raise ValueError(f"Missing control statement for control_id={control_id or 'unknown'}")

    output = llm_json(
        prompt=build_policy_coverage_prompt(control=control_model, policy_text=policy_text),
        model=model,
        temperature=0.1,
        purpose="gap_analysis",
    )
    return validate_policy_coverage_output(output)
