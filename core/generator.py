import csv
import json
import re
from pathlib import Path
from typing import Any, Dict, List, Optional

from domain.policies.blueprint import build_structured_policy_blueprint
from domain.policies.generator import generate_policy_markdown_from_blueprint


def load_json(path: str) -> Any:
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def save_text(path: str, content: str) -> str:
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        f.write(content)
    return path


def save_csv(path: str, rows: List[Dict[str, Any]]) -> str:
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    if not rows:
        with open(path, "w", newline="", encoding="utf-8") as f:
            f.write("")
        return path

    headers = list(rows[0].keys())
    with open(path, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=headers)
        w.writeheader()
        w.writerows(rows)
    return path


def normalize_policy_name(name: str) -> str:
    s = name.strip().lower()
    s = re.sub(r"[^a-z0-9]+", "_", s)
    s = re.sub(r"_+", "_", s).strip("_")
    return s or "policy"


def merge_controls(control_sets: List[Any], source_files: List[str]) -> List[Dict[str, Any]]:
    merged: List[Dict[str, Any]] = []
    seen = set()

    for idx, cs in enumerate(control_sets):
        src = source_files[idx] if idx < len(source_files) else "unknown_controls.json"

        if isinstance(cs, dict) and "controls" in cs:
            controls = cs["controls"]
        else:
            controls = cs

        if not isinstance(controls, list):
            continue

        for c in controls:
            if isinstance(c, str):
                continue
            if not isinstance(c, dict):
                continue

            statement = (c.get("statement") or "").strip()
            if not statement:
                continue

            key = f"{c.get('control_id','')}|{c.get('doc_id','')}|{str(c.get('page',''))}|{statement}".lower()
            if key in seen:
                continue
            seen.add(key)

            merged.append(
                {
                    "control_id": c.get("control_id", ""),
                    "doc_id": c.get("doc_id", ""),
                    "doc_title": c.get("doc_title", ""),
                    "page": str(c.get("page", "")),
                    "statement": statement,
                    "type": c.get("type", ""),
                    "topic": c.get("topic", ""),
                    "category": c.get("category", ""),
                    "control_type": c.get("control_type", ""),
                    "severity": c.get("severity", ""),
                    "policy_tags": c.get("policy_tags", []),
                    "implementation_hint": c.get("implementation_hint", ""),
                    "source_controls_file": src,
                }
            )

    return merged


def generate_structured_policy_blueprint(
    blueprint: Dict[str, Any],
    controls: List[Dict[str, Any]],
) -> Dict[str, Any]:
    """Compatibility wrapper for the new structured policy blueprint stage."""
    return build_structured_policy_blueprint(
        source_blueprint=blueprint,
        controls=controls,
    )


def generate_policy_md_from_blueprint(
    blueprint: Dict[str, Any],
    controls: List[Dict[str, Any]],
    model: Optional[str] = None,
) -> str:
    policy_blueprint = generate_structured_policy_blueprint(
        blueprint=blueprint,
        controls=controls,
    )
    return generate_policy_markdown_from_blueprint(
        policy_blueprint=policy_blueprint,
        model=model,
    )


def build_project_plan_rows(policy_name: str, controls: List[Dict[str, Any]], profile_summary: Dict[str, Any]) -> List[Dict[str, Any]]:
    rows = []

    business_type = profile_summary.get("business_type", "")
    lending_model = profile_summary.get("lending_model", "")

    for c in controls:
        if not isinstance(c, dict):
            continue

        owner = "Compliance"
        if c.get("control_type") == "Technical":
            owner = "Engineering / Security"
        elif c.get("control_type") == "Operational":
            owner = "Operations / Compliance"
        elif c.get("control_type") == "Governance":
            owner = "Leadership / Compliance"
        elif c.get("control_type") == "Legal":
            owner = "Legal / Compliance"

        if business_type == "Lending" and "kyc" in c.get("statement", "").lower():
            owner = "Compliance / Operations"

        if lending_model == "Partner-led" and (
            "partner" in c.get("statement", "").lower() or "csp" in c.get("statement", "").lower()
        ):
            owner = "Vendor Management / Compliance"

        task = c.get("implementation_hint") or f"Implement control: {c.get('statement', '')}"

        rows.append(
            {
                "policy_name": policy_name,
                "control_id": c.get("control_id", ""),
                "control_statement": c.get("statement", ""),
                "category": c.get("category", ""),
                "severity": c.get("severity", ""),
                "implementation_task": task,
                "owner": owner,
                "status": "Not started",
                "source_doc_title": c.get("doc_title", ""),
                "source_page": c.get("page", ""),
                "source_controls_file": c.get("source_controls_file", ""),
            }
        )

    return rows


def build_audit_register_rows(policy_name: str, controls: List[Dict[str, Any]], profile_summary: Dict[str, Any]) -> List[Dict[str, Any]]:
    rows = []

    for c in controls:
        if not isinstance(c, dict):
            continue

        evidence = "Policy / procedure / configuration / logs / report"
        if c.get("control_type") == "Technical":
            evidence = "Configuration screenshot / system log / access report"
        elif c.get("control_type") == "Governance":
            evidence = "Board-approved policy / committee minutes / approval record"
        elif c.get("control_type") == "Operational":
            evidence = "Process document / checklist / operational log"

        rows.append(
            {
                "policy_name": policy_name,
                "control_id": c.get("control_id", ""),
                "control_statement": c.get("statement", ""),
                "category": c.get("category", ""),
                "severity": c.get("severity", ""),
                "evidence_required": evidence,
                "review_frequency": "Annual",
                "evidence_owner": "Compliance / Control Owner",
                "source_doc_title": c.get("doc_title", ""),
                "source_page": c.get("page", ""),
                "source_controls_file": c.get("source_controls_file", ""),
            }
        )

    return rows


def build_traceability_rows(policy_name: str, controls: List[Dict[str, Any]], profile_summary: Dict[str, Any]) -> List[Dict[str, Any]]:
    rows = []
    for c in controls:
        if not isinstance(c, dict):
            continue

        rows.append(
            {
                "policy_name": policy_name,
                "control_id": c.get("control_id", ""),
                "policy_tag_match": ", ".join(c.get("policy_tags", [])) if isinstance(c.get("policy_tags"), list) else c.get("policy_tags", ""),
                "source_doc_title": c.get("doc_title", ""),
                "source_page": c.get("page", ""),
                "business_type": profile_summary.get("business_type", ""),
                "sector": profile_summary.get("sector", ""),
            }
        )
    return rows


def save_generation_run(policy_slug: str, blueprint: Dict[str, Any], policy_md: str) -> str:
    out_path = Path("data/generation_runs") / f"{policy_slug}_run.json"
    out_path.parent.mkdir(parents=True, exist_ok=True)

    payload = {
        "blueprint": blueprint,
        "generated_policy_preview": policy_md[:3000],
    }

    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)

    return str(out_path)
