import csv
import json
import tempfile
import time
from pathlib import Path
from typing import Dict, Any, List, Optional

from core.llm import llm_json
from core.ingest import pdf_to_pages, save_pages
from core.chunk import load_pages_jsonl
from core.controls import extract_controls_from_pages, save_controls_json, save_controls_csv
from core.control_registry import register_controls_to_master, map_controls_to_company
from core.generator import load_json, merge_controls


PROCESSED_DIR = Path("data/processed")
CONTROLS_DIR = Path("data/controls")

VALID_STATUSES = {
    "covered": "Covered",
    "partially covered": "Partially Covered",
    "partially_covered": "Partially Covered",
    "partial": "Partially Covered",
    "missing": "Missing",
}


def _normalize_status(value: Any) -> str:
    text = str(value or "").strip().lower()
    return VALID_STATUSES.get(text, "")


def _safe_text(value: Any) -> str:
    return str(value or "").strip()


def _build_base_result_row(control: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "control_id": control.get("control_id", ""),
        "statement": control.get("statement", ""),
        "category": control.get("category", ""),
        "severity": control.get("severity", ""),
        "source_doc_title": control.get("doc_title", ""),
        "source_page": control.get("page", ""),
    }


def _build_error_row(control: Dict[str, Any], error: Exception) -> Dict[str, Any]:
    row = _build_base_result_row(control)
    row.update(
        {
            "status": "Error",
            "reason": f"{type(error).__name__}: {str(error)}",
            "remediation": "",
        }
    )
    return row


def _validate_llm_output(out: Dict[str, Any]) -> Dict[str, str]:
    if not isinstance(out, dict):
        raise TypeError(f"llm_json returned {type(out).__name__}, expected dict")

    normalized_status = _normalize_status(out.get("status"))
    if not normalized_status:
        raise ValueError(
            f"Invalid LLM status: {out.get('status')!r}. Expected one of: Covered, Partially Covered, Missing"
        )

    return {
        "status": normalized_status,
        "reason": _safe_text(out.get("reason")),
        "remediation": _safe_text(out.get("remediation")),
    }


def analyze_single_control_against_policy(
    control: Dict[str, Any],
    policy_text: str,
    model: Optional[str] = None,
) -> Dict[str, Any]:
    statement = _safe_text(control.get("statement"))
    control_id = _safe_text(control.get("control_id"))

    if not statement:
        raise ValueError(f"Missing control statement for control_id={control_id or 'unknown'}")

    trimmed_policy_text = policy_text[:5000]

    prompt = f"""
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

    out = llm_json(
    prompt=prompt,
    model=model,
    temperature=0.1,
    )

    validated = _validate_llm_output(out)

    row = _build_base_result_row(control)
    row.update(validated)
    return row


def analyze_policy_gaps(
    controls: List[Dict[str, Any]],
    policy_text: str,
    model: Optional[str] = None,
    max_controls: int = 8,
) -> List[Dict[str, Any]]:
    if max_controls <= 0:
        return []

    results: List[Dict[str, Any]] = []
    controls_for_review = [c for c in controls if isinstance(c, dict)][:max_controls]

    for control in controls_for_review:
        try:
            row = analyze_single_control_against_policy(
                control=control,
                policy_text=policy_text,
                model=model,
            )
        except Exception as error:
            row = _build_error_row(control, error)

        results.append(row)

    return results


def summarize_gap_results(rows: List[Dict[str, Any]]) -> Dict[str, Any]:
    summary = {
        "total_reviewed": len(rows),
        "covered": 0,
        "partially_covered": 0,
        "missing": 0,
        "errors": 0,
    }

    for row in rows:
        status = _safe_text(row.get("status")).lower()

        if status == "covered":
            summary["covered"] += 1
        elif status == "partially covered":
            summary["partially_covered"] += 1
        elif status == "missing":
            summary["missing"] += 1
        else:
            summary["errors"] += 1

    return summary


def save_gap_analysis_json(rows: List[Dict[str, Any]], out_path: str) -> str:
    Path(out_path).parent.mkdir(parents=True, exist_ok=True)
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(rows, f, ensure_ascii=False, indent=2)
    return out_path


def save_gap_analysis_csv(rows: List[Dict[str, Any]], out_path: str) -> str:
    Path(out_path).parent.mkdir(parents=True, exist_ok=True)

    if not rows:
        with open(out_path, "w", encoding="utf-8", newline="") as f:
            f.write("")
        return out_path

    headers = list(rows[0].keys())
    with open(out_path, "w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=headers)
        writer.writeheader()
        writer.writerows(rows)

    return out_path


def save_gap_run_metadata(metadata: Dict[str, Any], out_path: str) -> str:
    Path(out_path).parent.mkdir(parents=True, exist_ok=True)
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(metadata, f, ensure_ascii=False, indent=2)
    return out_path


def load_controls_for_gap_analysis(
    controls_dir: str,
    selected_control_files: List[str],
) -> List[Dict[str, Any]]:
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
    """
    uploaded_files: list of Streamlit uploaded file objects
    """
    PROCESSED_DIR.mkdir(parents=True, exist_ok=True)
    CONTROLS_DIR.mkdir(parents=True, exist_ok=True)

    new_control_files: List[str] = []
    all_controls: List[Dict[str, Any]] = []

    for uploaded in uploaded_files:
        with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp:
            tmp.write(uploaded.read())
            tmp_path = tmp.name

        try:
            doc_title = uploaded.name
            doc_id = Path(uploaded.name).stem.lower().replace(" ", "_")

            pages = pdf_to_pages(tmp_path)

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

        finally:
            Path(tmp_path).unlink(missing_ok=True)

    return {
        "new_control_files": new_control_files,
        "merged_controls": all_controls,
    }


def run_gap_analysis_workflow(
    profile: Dict[str, Any],
    policy_text: str,
    control_source_mode: str,
    model: Optional[str] = None,
    max_controls: int = 8,
    selected_control_files: Optional[List[str]] = None,
    uploaded_regulation_files: Optional[List[Any]] = None,
) -> Dict[str, Any]:
    selected_control_files = selected_control_files or []
    uploaded_regulation_files = uploaded_regulation_files or []

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

    gap_rows = analyze_policy_gaps(
        controls=merged_controls,
        policy_text=policy_text,
        model=model,
        max_controls=max_controls,
    )

    summary = summarize_gap_results(gap_rows)

    run_id = f"gap_run_{int(time.time())}"
    metadata = {
        "run_id": run_id,
        "profile_name": profile.get("profile_name", ""),
        "control_source_mode": control_source_mode,
        "used_control_files": used_control_files,
        "new_control_files_created": new_control_files_created,
        "policy_text_length": len(policy_text),
        "max_controls_requested": max_controls,
        "controls_loaded": len(merged_controls),
        "controls_reviewed": len(gap_rows),
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