"""Shared helpers for turning regulation sources into control inputs.

These functions let multiple UI workflows consume a mix of:
- profile-selected regulation titles from the local catalog
- manually selected existing control files
- newly uploaded regulation documents
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List, Optional

from core.chunk import load_pages_jsonl
from core.control_registry import register_controls_to_master
from core.controls import extract_controls_from_pages, save_controls_csv, save_controls_json
from core.generator import load_json, merge_controls
from core.ingest import save_pages
from domain.regulations.catalog import resolve_control_files_for_regulations
from services.ingestion.file_loader import parse_uploaded_file


PROCESSED_DIR = Path("data/processed")
CONTROLS_DIR = Path("data/controls")


def load_controls_for_source_files(
    selected_control_files: List[str],
    controls_dir: str = str(CONTROLS_DIR),
) -> List[Dict[str, Any]]:
    """Load and merge one or more saved control files."""

    control_sets: List[List[Dict[str, Any]]] = []
    for file_name in selected_control_files:
        file_path = Path(controls_dir) / file_name
        control_sets.append(load_json(str(file_path)))

    return merge_controls(control_sets, selected_control_files)


def process_uploaded_regulations_to_controls(
    uploaded_files: List[Any],
    prefix: str = "QCB-SRC",
    min_len: int = 60,
    max_len: int = 500,
    model: Optional[str] = None,
    processed_dir: str = str(PROCESSED_DIR),
    controls_dir: str = str(CONTROLS_DIR),
) -> Dict[str, Any]:
    """Convert uploaded regulation PDFs into extracted control files."""

    processed_root = Path(processed_dir)
    controls_root = Path(controls_dir)
    processed_root.mkdir(parents=True, exist_ok=True)
    controls_root.mkdir(parents=True, exist_ok=True)

    new_control_files: List[str] = []
    all_controls: List[Dict[str, Any]] = []

    for uploaded in uploaded_files:
        parsed_upload = parse_uploaded_file(uploaded, file_type="pdf")
        doc_title = parsed_upload["source_name"]
        doc_id = Path(doc_title).stem.lower().replace(" ", "_")
        pages = parsed_upload.get("pages", [])

        out_pages = processed_root / f"{doc_id}_pages.jsonl"
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

        out_json = controls_root / f"{doc_id}_controls.json"
        out_csv = controls_root / f"{doc_id}_controls.csv"
        save_controls_json(controls, str(out_json))
        save_controls_csv(controls, str(out_csv))
        register_controls_to_master(controls)

        new_control_files.append(out_json.name)
        all_controls.extend(controls)

    return {
        "new_control_files": new_control_files,
        "merged_controls": all_controls,
    }


def resolve_regulation_control_inputs(
    selected_regulations: Optional[List[str]] = None,
    uploaded_regulation_files: Optional[List[Any]] = None,
    manual_control_files: Optional[List[str]] = None,
    model: Optional[str] = None,
    upload_prefix: str = "QCB-SRC",
    min_len: int = 60,
    max_len: int = 500,
    controls_dir: str = str(CONTROLS_DIR),
) -> Dict[str, Any]:
    """Resolve all regulation sources into one merged control list."""

    selected_regulations = list(dict.fromkeys(selected_regulations or []))
    manual_control_files = list(dict.fromkeys(manual_control_files or []))
    uploaded_regulation_files = uploaded_regulation_files or []

    catalog_resolution = resolve_control_files_for_regulations(
        selected_regulations=selected_regulations,
        controls_dir=controls_dir,
    )
    catalog_control_files = catalog_resolution["control_files"]
    missing_regulations = catalog_resolution["missing_regulations"]

    resolved_control_files = list(dict.fromkeys(catalog_control_files + manual_control_files))
    merged_controls = load_controls_for_source_files(
        selected_control_files=resolved_control_files,
        controls_dir=controls_dir,
    )

    new_control_files: List[str] = []
    if uploaded_regulation_files:
        processed_output = process_uploaded_regulations_to_controls(
            uploaded_files=uploaded_regulation_files,
            prefix=upload_prefix,
            min_len=min_len,
            max_len=max_len,
            model=model,
            controls_dir=controls_dir,
        )
        new_control_files = processed_output["new_control_files"]
        merged_controls = merge_controls(
            [merged_controls, processed_output["merged_controls"]],
            ["resolved_controls.json", "uploaded_controls.json"],
        )

    return {
        "selected_regulations": selected_regulations,
        "catalog_control_files": catalog_control_files,
        "manual_control_files": manual_control_files,
        "resolved_control_files": resolved_control_files,
        "missing_regulations": missing_regulations,
        "new_control_files": new_control_files,
        "merged_controls": merged_controls,
    }
