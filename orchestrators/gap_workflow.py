"""Workflow orchestration for policy gap analysis.

This module coordinates profile loading, regulation-to-control processing,
company-control mapping, dimension-level analysis, and persistence helpers.
It keeps sequencing concerns out of the UI and domain modules.
"""

import csv
import json
import time
from pathlib import Path
from typing import Any, Dict, List, Optional

from core.control_registry import map_controls_to_company
from core.profiler import list_profiles, load_profile
from domain.evidence.sufficiency import analyze_evidence_sufficiency
from domain.gaps.aggregator import aggregate_gap_result, build_error_gap_result, summarize_gap_results
from domain.gaps.implementation import analyze_implementation_gap
from domain.gaps.policy_coverage import analyze_policy_coverage
from orchestrators.regulation_source_workflow import (
    load_controls_for_source_files,
    process_uploaded_regulations_to_controls as shared_process_uploaded_regulations_to_controls,
    resolve_regulation_control_inputs,
)
from services.ingestion.file_loader import parse_file_bytes
from schemas.common import ensure_schema_list
from schemas.control import Control
from schemas.gap import GapAssessment


PROCESSED_DIR = Path("data/processed")
CONTROLS_DIR = Path("data/controls")
DEFAULT_PROFILES_DIR = Path("data/profiles")


def list_gap_control_files(controls_dir: str = str(CONTROLS_DIR)) -> List[str]:
    """Return existing extracted control files for the gap-analysis page."""

    directory = Path(controls_dir)
    if not directory.exists():
        return []
    return sorted(path.name for path in directory.glob("*_controls.json"))


def list_gap_profile_files(profiles_dir: str = str(DEFAULT_PROFILES_DIR)) -> List[str]:
    """Return saved business profiles available to the gap workflow."""

    return sorted(list_profiles(profiles_dir))


def parse_gap_policy_file(file_bytes: bytes, file_name: str) -> Dict[str, Any]:
    """Parse an uploaded policy document via the shared ingestion layer."""

    return parse_file_bytes(file_bytes=file_bytes, source_name=file_name)


def save_gap_analysis_json(rows: List[Dict[str, Any]], out_path: str) -> str:
    """Persist gap rows as JSON."""
    Path(out_path).parent.mkdir(parents=True, exist_ok=True)
    with open(out_path, "w", encoding="utf-8") as handle:
        json.dump(rows, handle, ensure_ascii=False, indent=2)
    return out_path


def save_gap_analysis_csv(rows: List[Dict[str, Any]], out_path: str) -> str:
    """Persist gap rows as CSV."""
    Path(out_path).parent.mkdir(parents=True, exist_ok=True)

    if not rows:
        with open(out_path, "w", encoding="utf-8", newline="") as handle:
            handle.write("")
        return out_path

    headers = list(rows[0].keys())
    with open(out_path, "w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=headers)
        writer.writeheader()
        writer.writerows(rows)

    return out_path


def save_gap_run_metadata(metadata: Dict[str, Any], out_path: str) -> str:
    """Persist workflow metadata for a gap-analysis run."""
    Path(out_path).parent.mkdir(parents=True, exist_ok=True)
    with open(out_path, "w", encoding="utf-8") as handle:
        json.dump(metadata, handle, ensure_ascii=False, indent=2)
    return out_path


def load_profile_for_gap_workflow(
    profile_name: str,
    profiles_dir: str = str(DEFAULT_PROFILES_DIR),
) -> Dict[str, Any]:
    """Load a saved business profile by file name for the workflow."""
    profile_path = Path(profiles_dir) / profile_name
    if not profile_path.exists():
        raise FileNotFoundError(f"Business profile not found: {profile_path}")
    return load_profile(str(profile_path))


def load_controls_for_gap_analysis(
    controls_dir: str,
    selected_control_files: List[str],
) -> List[Dict[str, Any]]:
    """Load and merge selected control files into one review set."""
    return load_controls_for_source_files(
        selected_control_files=selected_control_files,
        controls_dir=controls_dir,
    )


def process_uploaded_regulations_to_controls(
    uploaded_files: List[Any],
    prefix: str = "QCB-GAP",
    min_len: int = 60,
    max_len: int = 500,
    model: Optional[str] = None,
) -> Dict[str, Any]:
    """Convert uploaded regulation PDFs into extracted control files."""
    return shared_process_uploaded_regulations_to_controls(
        uploaded_files=uploaded_files,
        prefix=prefix,
        min_len=min_len,
        max_len=max_len,
        model=model,
        processed_dir=str(PROCESSED_DIR),
        controls_dir=str(CONTROLS_DIR),
    )


def analyze_gap_dimensions(
    controls: List[Dict[str, Any]],
    policy_text: str,
    company_control_rows: Optional[List[Dict[str, Any]]] = None,
    model: Optional[str] = None,
    max_controls: int = 8,
) -> List[GapAssessment]:
    """Run all current gap dimensions and aggregate the result rows."""
    if max_controls <= 0:
        return []

    company_control_models = ensure_schema_list(company_control_rows or [], Control)
    company_control_index = {
        control.control_id: control
        for control in company_control_models
        if control.control_id
    }

    results: List[GapAssessment] = []
    controls_for_review = ensure_schema_list(controls, Control)[:max_controls]

    for control in controls_for_review:
        company_control = company_control_index.get(control.control_id)

        try:
            policy_coverage = analyze_policy_coverage(control=control, policy_text=policy_text, model=model)
            implementation = analyze_implementation_gap(control=control, company_control=company_control)
            evidence_sufficiency = analyze_evidence_sufficiency(control=control, company_control=company_control)
            row = aggregate_gap_result(
                control=control,
                policy_coverage=policy_coverage,
                implementation=implementation,
                evidence_sufficiency=evidence_sufficiency,
            )
        except Exception as error:
            row = build_error_gap_result(control, error)

        results.append(row)

    return results


def run_gap_workflow(
    policy_text: str,
    control_source_mode: Optional[str] = None,
    model: Optional[str] = None,
    max_controls: int = 8,
    selected_control_files: Optional[List[str]] = None,
    selected_regulations: Optional[List[str]] = None,
    uploaded_regulation_files: Optional[List[Any]] = None,
    profile: Optional[Dict[str, Any]] = None,
    profile_name: Optional[str] = None,
    profiles_dir: str = str(DEFAULT_PROFILES_DIR),
) -> Dict[str, Any]:
    """Run the end-to-end gap workflow while keeping the page layer thin."""
    selected_control_files = selected_control_files or []
    selected_regulations = selected_regulations or []
    uploaded_regulation_files = uploaded_regulation_files or []

    if profile is None:
        if not profile_name:
            raise ValueError("A profile or profile_name is required to run gap analysis.")
        profile = load_profile_for_gap_workflow(profile_name=profile_name, profiles_dir=profiles_dir)

    control_resolution = resolve_regulation_control_inputs(
        selected_regulations=selected_regulations,
        uploaded_regulation_files=uploaded_regulation_files,
        manual_control_files=selected_control_files,
        model=model,
        upload_prefix="QCB-GAP",
        controls_dir=str(CONTROLS_DIR),
    )
    merged_controls = control_resolution["merged_controls"]
    used_control_files = list(
        dict.fromkeys(control_resolution["resolved_control_files"] + control_resolution["new_control_files"])
    )
    new_control_files_created = control_resolution["new_control_files"]

    if not control_source_mode:
        if selected_regulations and uploaded_regulation_files:
            control_source_mode = "profile_and_upload"
        elif selected_regulations:
            control_source_mode = "profile_regulations"
        elif selected_control_files and uploaded_regulation_files:
            control_source_mode = "existing_and_upload"
        elif uploaded_regulation_files:
            control_source_mode = "upload_new"
        else:
            control_source_mode = "existing"

    if not merged_controls:
        raise ValueError("No controls could be resolved from the selected regulation sources.")

    company_control_rows = map_controls_to_company(profile, merged_controls)
    gap_row_models = analyze_gap_dimensions(
        controls=merged_controls,
        policy_text=policy_text,
        company_control_rows=company_control_rows,
        model=model,
        max_controls=max_controls,
    )
    gap_rows = [row.to_dict() for row in gap_row_models]
    summary = summarize_gap_results(gap_row_models)

    run_id = f"gap_run_{int(time.time())}"
    metadata = {
        "run_id": run_id,
        "profile_name": profile.get("profile_name", profile_name or ""),
        "control_source_mode": control_source_mode,
        "selected_regulations": selected_regulations,
        "used_control_files": used_control_files,
        "new_control_files_created": new_control_files_created,
        "missing_regulations": control_resolution["missing_regulations"],
        "policy_text_length": len(policy_text),
        "max_controls_requested": max_controls,
        "controls_loaded": len(merged_controls),
        "controls_reviewed": len(gap_row_models),
        "model_used": model,
        "summary": summary,
    }

    return {
        "run_id": run_id,
        "gap_rows": gap_rows,
        "summary": summary,
        "used_control_files": used_control_files,
        "new_control_files_created": new_control_files_created,
        "company_control_rows": company_control_rows,
        "run_metadata": metadata,
    }
