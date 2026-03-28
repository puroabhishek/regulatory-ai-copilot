"""Compatibility wrapper for gap-analysis workflow functions.

New code should import orchestration and domain helpers from:
- ``orchestrators.gap_workflow``
- ``domain.gaps.*``
- ``domain.evidence.sufficiency``

This module remains in place temporarily so existing callers keep working while
the refactor is in progress.
"""

from typing import Any, Dict, List, Optional

from domain.evidence.sufficiency import analyze_evidence_sufficiency
from domain.gaps.aggregator import aggregate_gap_result, build_error_gap_result, summarize_gap_results
from domain.gaps.implementation import analyze_implementation_gap
from domain.gaps.policy_coverage import analyze_policy_coverage
from orchestrators.gap_workflow import (
    analyze_gap_dimensions,
    load_controls_for_gap_analysis,
    process_uploaded_regulations_to_controls,
    run_gap_workflow,
    save_gap_analysis_csv,
    save_gap_analysis_json,
    save_gap_run_metadata,
)


def analyze_single_control_against_policy(
    control: Dict[str, Any],
    policy_text: str,
    model: Optional[str] = None,
) -> Dict[str, Any]:
    """Legacy wrapper that returns one aggregated row for a control."""
    policy_coverage = analyze_policy_coverage(control=control, policy_text=policy_text, model=model)
    implementation = analyze_implementation_gap(control=control, company_control=None)
    evidence_sufficiency = analyze_evidence_sufficiency(control=control, company_control=None)
    return aggregate_gap_result(
        control=control,
        policy_coverage=policy_coverage,
        implementation=implementation,
        evidence_sufficiency=evidence_sufficiency,
    ).to_dict()


def analyze_policy_gaps(
    controls: List[Dict[str, Any]],
    policy_text: str,
    model: Optional[str] = None,
    max_controls: int = 8,
) -> List[Dict[str, Any]]:
    """Legacy batch wrapper around the refactored multi-dimension analyzers."""
    return [row.to_dict() for row in analyze_gap_dimensions(
        controls=controls,
        policy_text=policy_text,
        company_control_rows=None,
        model=model,
        max_controls=max_controls,
    )]


def run_gap_analysis_workflow(
    profile: Dict[str, Any],
    policy_text: str,
    control_source_mode: str,
    model: Optional[str] = None,
    max_controls: int = 8,
    selected_control_files: Optional[List[str]] = None,
    uploaded_regulation_files: Optional[List[Any]] = None,
) -> Dict[str, Any]:
    """Legacy orchestration entrypoint preserved for backward compatibility."""
    return run_gap_workflow(
        profile=profile,
        policy_text=policy_text,
        control_source_mode=control_source_mode,
        model=model,
        max_controls=max_controls,
        selected_control_files=selected_control_files,
        uploaded_regulation_files=uploaded_regulation_files,
    )


__all__ = [
    "analyze_gap_dimensions",
    "analyze_policy_gaps",
    "analyze_single_control_against_policy",
    "load_controls_for_gap_analysis",
    "process_uploaded_regulations_to_controls",
    "run_gap_analysis_workflow",
    "save_gap_analysis_csv",
    "save_gap_analysis_json",
    "save_gap_run_metadata",
    "summarize_gap_results",
    "build_error_gap_result",
]
