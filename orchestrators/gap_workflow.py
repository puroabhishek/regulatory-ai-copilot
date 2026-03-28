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

from core.chunk import load_pages_jsonl
from core.control_registry import map_controls_to_company, register_controls_to_master
from core.controls import extract_controls_from_pages, save_controls_csv, save_controls_json
from core.generator import load_json, merge_controls
from core.ingest import save_pages
from core.profiler import list_profiles, load_profile
from domain.evidence.sufficiency import analyze_evidence_sufficiency
from domain.gaps.aggregator import aggregate_gap_result, build_error_gap_result, summarize_gap_results
from domain.gaps.implementation import analyze_implementation_gap
from domain.gaps.policy_coverage import analyze_policy_coverage
from services.ingestion.file_loader import parse_file_bytes, parse_uploaded_file
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
    control_sets: List[List[Dict[str, Any]]] = []

    for file_name in selected_control_files:
        file_path = Path(controls_dir) / file_name
        control_sets.append(load_json(str(file_path)))

    return merge_controls(control_sets, selected_control_files)


def process_uploaded_regulations_to_controls(
    uploaded_files: List[Any],
    prefix: str = "QCB-GAP",
    min_len: int = 60,
    max_len: int = 500,
    model: Optional[str] = None,
) -> Dict[str, Any]:
    """Convert uploaded regulation PDFs into extracted control files."""
    PROCESSED_DIR.mkdir(parents=True, exist_ok=True)
    CONTROLS_DIR.mkdir(parents=True, exist_ok=True)

    new_control_files: List[str] = []
    all_controls: List[Dict[str, Any]] = []

    for uploaded in uploaded_files:
        parsed_upload = parse_uploaded_file(uploaded, file_type="pdf")
        doc_title = parsed_upload["source_name"]
        doc_id = Path(doc_title).stem.lower().replace(" ", "_")
        pages = parsed_upload.get("pages", [])

        out_pages = PROCESSED_DIR / f"{doc_id}_pages.jsonl"
        save_pages(
            pages=pages,
            out_path=str(out_pages),
            doc_id=doc_id,
            doc_title=doc_title,
        )

        pages_loaded = load_pages_jsonl(str(out_pages))
        controls = extract_controls_from_pages(
            pages=pages_loaded,
            doc_id=doc_id,
            doc_title=doc_title,
            prefix=prefix,
            min_len=min_len,
            max_len=max_len,
            model=model,
        )

        out_json = CONTROLS_DIR / f"{doc_id}_controls.json"
        out_csv = CONTROLS_DIR / f"{doc_id}_controls.csv"
        save_controls_json(controls, str(out_json))
        save_controls_csv(controls, str(out_csv))
        register_controls_to_master(controls)

        new_control_files.append(out_json.name)
        all_controls.extend(controls)

    return {
        "new_control_files": new_control_files,
        "merged_controls": all_controls,
    }


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
    control_source_mode: str,
    model: Optional[str] = None,
    max_controls: int = 8,
    selected_control_files: Optional[List[str]] = None,
    uploaded_regulation_files: Optional[List[Any]] = None,
    profile: Optional[Dict[str, Any]] = None,
    profile_name: Optional[str] = None,
    profiles_dir: str = str(DEFAULT_PROFILES_DIR),
) -> Dict[str, Any]:
    """Run the end-to-end gap workflow while keeping the page layer thin."""
    selected_control_files = selected_control_files or []
    uploaded_regulation_files = uploaded_regulation_files or []

    if profile is None:
        if not profile_name:
            raise ValueError("A profile or profile_name is required to run gap analysis.")
        profile = load_profile_for_gap_workflow(profile_name=profile_name, profiles_dir=profiles_dir)

    used_control_files: List[str] = []
    new_control_files_created: List[str] = []
    merged_controls: List[Dict[str, Any]] = []

    if control_source_mode == "existing":
        merged_controls = load_controls_for_gap_analysis(
            controls_dir=str(CONTROLS_DIR),
            selected_control_files=selected_control_files,
        )
        used_control_files = selected_control_files
    elif control_source_mode == "upload_new":
        processed_output = process_uploaded_regulations_to_controls(
            uploaded_files=uploaded_regulation_files,
            prefix="QCB-GAP",
            min_len=60,
            max_len=500,
            model=model,
        )
        merged_controls = processed_output["merged_controls"]
        new_control_files_created = processed_output["new_control_files"]
        used_control_files = new_control_files_created
    else:
        raise ValueError("control_source_mode must be 'existing' or 'upload_new'")

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
        "used_control_files": used_control_files,
        "new_control_files_created": new_control_files_created,
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
