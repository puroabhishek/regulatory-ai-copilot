"""Pydantic schemas for policy gap analysis."""

from __future__ import annotations

from typing import Optional, Union

from schemas.common import SchemaModel


PageValue = Optional[Union[int, str]]


class PolicyCoverageAssessment(SchemaModel):
    """Assessment of whether a policy document covers a specific control."""

    status: str = ""
    reason: str = ""
    remediation: str = ""


class ImplementationAssessment(SchemaModel):
    """Assessment of the current implementation state for a control."""

    status: str = "Not Assessed"
    reason: str = ""
    remediation: str = ""
    owner: str = ""
    applicability: str = "Applicable"


class EvidenceSufficiencyAssessment(SchemaModel):
    """Assessment of whether current evidence is enough for review."""

    status: str = ""
    reason: str = ""
    remediation: str = ""
    evidence_type: str = ""
    evidence_link: str = ""


class GapAssessment(SchemaModel):
    """Flattened gap result row used by the current UI, exports, and wrappers."""

    control_id: str = ""
    statement: str = ""
    category: str = ""
    severity: str = ""
    source_doc_title: str = ""
    source_page: PageValue = ""
    status: str = ""
    reason: str = ""
    remediation: str = ""
    policy_coverage_status: str = ""
    policy_coverage_reason: str = ""
    policy_coverage_remediation: str = ""
    implementation_status: str = ""
    implementation_reason: str = ""
    implementation_remediation: str = ""
    evidence_sufficiency_status: str = ""
    evidence_sufficiency_reason: str = ""
    evidence_sufficiency_remediation: str = ""
    owner: str = ""
    applicability: str = ""
    evidence_type: str = ""
    evidence_link: str = ""
