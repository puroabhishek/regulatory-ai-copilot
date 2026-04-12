"""Structured policy blueprint builders.

This module creates a schema-like policy drafting blueprint from the existing
saved policy blueprint metadata plus the selected controls. It is intentionally
pure: no file I/O and no UI concerns live here.
"""

from dataclasses import asdict, dataclass, field
from typing import Any, Dict, List


@dataclass
class PolicyDefinition:
    """A structured definition entry for the policy blueprint."""

    term: str
    definition: str


@dataclass
class PolicyResponsibility:
    """A structured role-to-responsibility mapping for the policy blueprint."""

    role: str
    responsibility: str


@dataclass
class PolicyStatementBlueprint:
    """A structured policy statement tied back to one or more controls."""

    statement_id: str
    heading: str
    statement: str
    related_control_ids: List[str] = field(default_factory=list)
    topic: str = ""
    severity: str = ""


@dataclass
class StructuredPolicyBlueprint:
    """Schema-like plan used as the drafting input for final markdown generation."""

    title: str
    objective: str
    scope: List[str]
    definitions: List[PolicyDefinition]
    responsibilities: List[PolicyResponsibility]
    policy_statements: List[PolicyStatementBlueprint]
    procedures: List[str]
    records: List[str]
    exceptions: str
    review_cycle: str
    drafting_instructions: str = ""
    style_reference_excerpt: str = ""
    source_context: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Convert the structured blueprint into a serializable dictionary."""
        return asdict(self)


def _safe_text(value: Any) -> str:
    return str(value or "").strip()


def _profile_summary(source_blueprint: Dict[str, Any]) -> Dict[str, Any]:
    return source_blueprint.get("profile_summary", {}) or {}


def _source_context(source_blueprint: Dict[str, Any]) -> Dict[str, Any]:
    return source_blueprint.get("source_context", {}) or {}


def _controls_sample(controls: List[Dict[str, Any]], limit: int = 12) -> List[Dict[str, Any]]:
    sample: List[Dict[str, Any]] = []
    for control in controls:
        if not isinstance(control, dict):
            continue
        sample.append(control)
        if len(sample) >= limit:
            break
    return sample


def _build_objective(title: str, profile_summary: Dict[str, Any]) -> str:
    sector = _safe_text(profile_summary.get("sector"))
    business_type = _safe_text(profile_summary.get("business_type"))
    country = _safe_text(profile_summary.get("country"))
    regulator = _safe_text(profile_summary.get("regulator"))

    parts = [part for part in [sector, business_type, country] if part]
    business_context = " / ".join(parts) or "business"

    if regulator:
        return (
            f"Define the principles, responsibilities, and mandatory requirements for the {title} "
            f"for the {business_context} operating context, aligned to {regulator} expectations."
        )

    return (
        f"Define the principles, responsibilities, and mandatory requirements for the {title} "
        f"for the {business_context} operating context."
    )


def _build_scope(profile_summary: Dict[str, Any]) -> List[str]:
    scope = [
        "Applies to all employees, contractors, and relevant third parties supporting the covered business activities.",
        "Applies to systems, processes, records, and data used to deliver the covered services.",
    ]

    business_model = _safe_text(profile_summary.get("business_model"))
    target_customers = _safe_text(profile_summary.get("target_customers"))
    cloud_use = _safe_text(profile_summary.get("cloud_use"))
    hosting_region = _safe_text(profile_summary.get("hosting_region"))
    data_residency_required = _safe_text(profile_summary.get("data_residency_required"))
    lending_model = _safe_text(profile_summary.get("lending_model"))

    if business_model or target_customers:
        scope.append(
            f"Covers the operating model for {business_model or 'the business'} services serving {target_customers or 'the target customer base'}."
        )
    if cloud_use:
        scope.append(
            f"Includes supporting technology and hosting arrangements where cloud usage is {cloud_use.lower()}."
        )
    if hosting_region or data_residency_required:
        scope.append(
            f"Includes data-handling and hosting arrangements relevant to {hosting_region or 'the applicable hosting region'} and residency obligations set to {data_residency_required or 'business-specific requirements'}."
        )
    if lending_model and lending_model != "Not applicable":
        scope.append(
            f"Includes partner, lending, and service-delivery dependencies relevant to the {lending_model} operating model."
        )

    return scope


def _build_definitions(profile_summary: Dict[str, Any], controls: List[Dict[str, Any]]) -> List[PolicyDefinition]:
    definitions = [
        PolicyDefinition(
            term="Policy Owner",
            definition="The function accountable for maintaining this policy, overseeing implementation, and coordinating periodic review.",
        ),
        PolicyDefinition(
            term="Control Owner",
            definition="The person or function accountable for implementing, operating, and evidencing a specific control or requirement.",
        ),
    ]

    if _safe_text(profile_summary.get("handles_pii")).lower() == "yes":
        definitions.append(
            PolicyDefinition(
                term="Personal Data",
                definition="Any information relating to an identified or identifiable natural person handled by the business.",
            )
        )

    if _safe_text(profile_summary.get("cloud_use")).lower() == "yes":
        definitions.append(
            PolicyDefinition(
                term="Cloud Service Provider",
                definition="A third-party provider delivering hosted infrastructure, platform, or software services used by the business.",
            )
        )

    if any("risk" in _safe_text(control.get("topic")).lower() for control in controls if isinstance(control, dict)):
        definitions.append(
            PolicyDefinition(
                term="Risk Assessment",
                definition="A documented process used to identify, assess, and track risks relevant to the policy domain and related controls.",
            )
        )

    return definitions


def _build_responsibilities(profile_summary: Dict[str, Any], controls: List[Dict[str, Any]]) -> List[PolicyResponsibility]:
    responsibilities = [
        PolicyResponsibility(
            role="Leadership / Management",
            responsibility="Approve the policy direction, provide oversight, and ensure appropriate resources for implementation.",
        ),
        PolicyResponsibility(
            role="Compliance",
            responsibility="Interpret regulatory obligations, maintain the policy, monitor adherence, and coordinate reviews and remediation.",
        ),
        PolicyResponsibility(
            role="Control Owners",
            responsibility="Implement the assigned controls, maintain supporting evidence, and address gaps in a timely manner.",
        ),
    ]

    if any(_safe_text(control.get("control_type")) == "Technical" for control in controls if isinstance(control, dict)):
        responsibilities.append(
            PolicyResponsibility(
                role="Engineering / Security",
                responsibility="Implement and maintain technical safeguards, system configurations, and technical evidence required by the policy.",
            )
        )

    lending_model = _safe_text(profile_summary.get("lending_model"))
    if lending_model == "Partner-led":
        responsibilities.append(
            PolicyResponsibility(
                role="Vendor Management / Compliance",
                responsibility="Oversee partner and outsourced service arrangements, including monitoring of obligations delegated to third parties.",
            )
        )

    return responsibilities


def _statement_heading(control: Dict[str, Any], index: int) -> str:
    heading = _safe_text(control.get("category")) or _safe_text(control.get("topic"))
    return heading or f"Policy Statement {index}"


def _statement_body(control: Dict[str, Any]) -> str:
    implementation_hint = _safe_text(control.get("implementation_hint"))
    statement = _safe_text(control.get("statement"))
    return implementation_hint or statement


def _build_policy_statements(controls: List[Dict[str, Any]]) -> List[PolicyStatementBlueprint]:
    statements: List[PolicyStatementBlueprint] = []

    for index, control in enumerate(_controls_sample(controls), start=1):
        statements.append(
            PolicyStatementBlueprint(
                statement_id=f"PS-{index}",
                heading=_statement_heading(control, index),
                statement=_statement_body(control),
                related_control_ids=[_safe_text(control.get("control_id"))] if _safe_text(control.get("control_id")) else [],
                topic=_safe_text(control.get("topic")),
                severity=_safe_text(control.get("severity")),
            )
        )

    return statements


def _build_procedures(profile_summary: Dict[str, Any], controls: List[Dict[str, Any]]) -> List[str]:
    procedures = [
        "Document and approve the control implementation approach, including policy ownership and evidence expectations.",
        "Implement the required controls and operational practices aligned to the policy statements in this blueprint.",
        "Monitor adherence, record exceptions, and track remediation actions through periodic review.",
    ]

    if _safe_text(profile_summary.get("handles_pii")).lower() == "yes":
        procedures.append("Handle personal and sensitive data in line with approved processing, access, retention, and protection requirements.")

    if any("review" in _safe_text(control.get("statement")).lower() for control in controls if isinstance(control, dict)):
        procedures.append("Perform periodic control reviews and retain evidence of management review, corrective action, and closure.")

    return procedures


def _build_records(controls: List[Dict[str, Any]]) -> List[str]:
    records = [
        "Approved policy and version history",
        "Control implementation evidence and supporting artifacts",
        "Review logs, issue trackers, and remediation records",
    ]

    if any(_safe_text(control.get("control_type")) == "Technical" for control in controls if isinstance(control, dict)):
        records.append("System configurations, technical logs, and access review outputs")

    if any("audit" in _safe_text(control.get("statement")).lower() for control in controls if isinstance(control, dict)):
        records.append("Audit reports, management responses, and follow-up actions")

    return records


def _build_exceptions() -> str:
    return (
        "Exceptions must be documented, risk-assessed, approved by the appropriate authority, and reviewed until resolved or formally retired."
    )


def _build_review_cycle(source_blueprint: Dict[str, Any]) -> str:
    drafting_instructions = _safe_text(source_blueprint.get("drafting_instructions"))
    if "quarter" in drafting_instructions.lower():
        return "Quarterly or upon material regulatory or business change"
    return "Annual or upon material regulatory or business change"


def build_structured_policy_blueprint(
    source_blueprint: Dict[str, Any],
    controls: List[Dict[str, Any]],
) -> Dict[str, Any]:
    """Create the structured policy blueprint used for final markdown drafting."""
    title = _safe_text(source_blueprint.get("policy_name")) or "Policy"
    profile_summary = _profile_summary(source_blueprint)
    source_context = _source_context(source_blueprint)

    plan = StructuredPolicyBlueprint(
        title=title,
        objective=_build_objective(title, profile_summary),
        scope=_build_scope(profile_summary),
        definitions=_build_definitions(profile_summary, controls),
        responsibilities=_build_responsibilities(profile_summary, controls),
        policy_statements=_build_policy_statements(controls),
        procedures=_build_procedures(profile_summary, controls),
        records=_build_records(controls),
        exceptions=_build_exceptions(),
        review_cycle=_build_review_cycle(source_blueprint),
        drafting_instructions=_safe_text(source_blueprint.get("drafting_instructions")),
        style_reference_excerpt=_safe_text(source_blueprint.get("sample_policy_text"))[:1200],
        source_context={
            **source_context,
            "policy_name": title,
            "applicable_regulations": list(source_blueprint.get("applicable_regulations", []) or []),
            "selected_control_files": list(source_blueprint.get("selected_control_files", []) or []),
            "selected_profile_file": _safe_text(source_blueprint.get("selected_profile_file")),
            "profile_summary": profile_summary,
            "controls_considered": len([control for control in controls if isinstance(control, dict)]),
        },
    )

    return plan.to_dict()
