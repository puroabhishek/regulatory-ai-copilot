"""Workflow helpers for control extraction and control-registry management."""

from __future__ import annotations

import time
from pathlib import Path
from typing import Any, Dict, List, Optional

from core.chunk import load_pages_jsonl
from core.control_registry import (
    get_company_control_summary,
    load_company_controls,
    load_controls_master,
    register_controls_to_master,
    update_company_control,
)
from core.controls import extract_controls_from_pages, save_controls_csv, save_controls_json


PROCESSED_DIR = Path("data/processed")
CONTROLS_DIR = Path("data/controls")


def list_processed_regulation_files(processed_dir: str = str(PROCESSED_DIR)) -> List[str]:
    """Return processed regulation files that can be turned into controls."""

    directory = Path(processed_dir)
    if not directory.exists():
        return []
    return sorted(path.name for path in directory.glob("*_pages.jsonl"))


def list_extracted_control_files(controls_dir: str = str(CONTROLS_DIR)) -> List[str]:
    """Return saved extracted control files."""

    directory = Path(controls_dir)
    if not directory.exists():
        return []
    return sorted(path.name for path in directory.glob("*_controls.json"))


def extract_controls_from_processed_file(
    selected_file: str,
    prefix: str,
    min_len: int,
    max_len: int,
    model: Optional[str] = None,
    processed_dir: str = str(PROCESSED_DIR),
    controls_dir: str = str(CONTROLS_DIR),
) -> Dict[str, Any]:
    """Run the current extraction flow for a saved processed regulation file."""

    start_time = time.time()
    pages = load_pages_jsonl(str(Path(processed_dir) / selected_file))
    doc_id = pages[0].get("doc_id", Path(selected_file).stem.replace("_pages", "")) if pages else Path(selected_file).stem
    doc_title = pages[0].get("doc_title", selected_file) if pages else selected_file

    controls = extract_controls_from_pages(
        pages=pages,
        doc_id=doc_id,
        doc_title=doc_title,
        prefix=prefix,
        min_len=min_len,
        max_len=max_len,
        model=model,
    )

    out_json = Path(controls_dir) / f"{doc_id}_controls.json"
    out_csv = Path(controls_dir) / f"{doc_id}_controls.csv"
    save_controls_json(controls, str(out_json))
    save_controls_csv(controls, str(out_csv))
    added_to_master = register_controls_to_master(controls)

    return {
        "doc_id": doc_id,
        "doc_title": doc_title,
        "controls": controls,
        "out_json": str(out_json),
        "out_csv": str(out_csv),
        "added_to_master": added_to_master,
        "elapsed_seconds": round(time.time() - start_time, 2),
    }


def get_control_registry_page_data() -> Dict[str, Any]:
    """Load the registry data needed for the control-cockpit page."""

    return {
        "summary": get_company_control_summary(),
        "master_rows": load_controls_master(),
        "company_rows": load_company_controls(),
    }


def update_company_control_record(control_id: str, updates: Dict[str, Any]) -> Dict[str, Any]:
    """Update one company control and return the refreshed inventory snapshot."""

    updated = update_company_control(control_id=control_id, updates=updates)
    company_rows = load_company_controls()
    selected_row = next((row for row in company_rows if row.get("control_id") == control_id), None)

    return {
        "updated": updated,
        "selected_row": selected_row,
        "company_rows": company_rows,
    }
