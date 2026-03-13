import json
import csv
from pathlib import Path
from typing import List, Dict, Any


MASTER_PATH = Path("data/control_registry/controls_master.json")
COMPANY_PATH = Path("data/control_registry/company_controls.json")
COMPANY_CSV_PATH = Path("data/control_registry/company_controls.csv")


def _load_json(path: Path):
    if not path.exists():
        return []
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def _save_json(path: Path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def _save_csv(path: Path, rows: List[Dict[str, Any]]):
    path.parent.mkdir(parents=True, exist_ok=True)
    if not rows:
        with open(path, "w", encoding="utf-8", newline="") as f:
            f.write("")
        return

    headers = list(rows[0].keys())
    with open(path, "w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=headers)
        writer.writeheader()
        writer.writerows(rows)


def load_controls_master() -> List[Dict[str, Any]]:
    return _load_json(MASTER_PATH)


def save_controls_master(rows: List[Dict[str, Any]]):
    _save_json(MASTER_PATH, rows)


def load_company_controls() -> List[Dict[str, Any]]:
    return _load_json(COMPANY_PATH)


def save_company_controls(rows: List[Dict[str, Any]]):
    _save_json(COMPANY_PATH, rows)
    _save_csv(COMPANY_CSV_PATH, rows)


def register_controls_to_master(controls: List[Dict[str, Any]]) -> int:
    """
    Adds extracted controls to the global control master registry.
    Dedupes by control_id.
    """
    existing = load_controls_master()
    seen_ids = {r.get("control_id", "") for r in existing}

    added = 0
    for c in controls:
        cid = c.get("control_id", "")
        if not cid or cid in seen_ids:
            continue

        existing.append(
            {
                "control_id": c.get("control_id", ""),
                "doc_id": c.get("doc_id", ""),
                "doc_title": c.get("doc_title", ""),
                "page": c.get("page", ""),
                "statement": c.get("statement", ""),
                "type": c.get("type", ""),
                "topic": c.get("topic", ""),
                "category": c.get("category", ""),
                "control_type": c.get("control_type", ""),
                "severity": c.get("severity", ""),
                "policy_tags": c.get("policy_tags", []),
                "implementation_hint": c.get("implementation_hint", ""),
                "evidence_type": infer_evidence_type(c),
                "automation_possible": infer_automation_possible(c),
            }
        )
        seen_ids.add(cid)
        added += 1

    save_controls_master(existing)
    return added


def infer_evidence_type(control: Dict[str, Any]) -> str:
    control_type = (control.get("control_type") or "").lower()
    statement = (control.get("statement") or "").lower()

    if control_type == "technical":
        return "Configuration / Logs / Screenshot"
    if control_type == "governance":
        return "Policy / Approval / Minutes"
    if control_type == "operational":
        return "Checklist / SOP / Operational Record"
    if "audit" in statement or "review" in statement:
        return "Audit Report / Review Record"
    return "Documentary Evidence"


def infer_automation_possible(control: Dict[str, Any]) -> str:
    control_type = (control.get("control_type") or "").lower()
    statement = (control.get("statement") or "").lower()

    if control_type == "technical":
        return "Yes"
    if "log" in statement or "configuration" in statement or "encryption" in statement:
        return "Yes"
    return "No"


def map_controls_to_company(profile: Dict[str, Any], selected_controls: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Creates company-specific control inventory from selected controls + profile.
    """
    company_name = profile.get("profile_name", "")
    business_type = profile.get("business_type", "")
    sector = profile.get("sector", "")
    lending_model = profile.get("lending_model", "")

    rows = []
    for c in selected_controls:
        if not isinstance(c, dict):
            continue

        applicability = "Applicable"
        reason = "Selected in blueprint"

        statement = (c.get("statement") or "").lower()

        if business_type != "Lending" and "kyc" in statement:
            applicability = "Needs Review"
            reason = "KYC-related control may not fully apply outside lending"

        owner = "Compliance"
        if c.get("control_type") == "Technical":
            owner = "Engineering / Security"
        elif c.get("control_type") == "Operational":
            owner = "Operations / Compliance"
        elif c.get("control_type") == "Governance":
            owner = "Leadership / Compliance"
        elif c.get("control_type") == "Legal":
            owner = "Legal / Compliance"

        if business_type == "Lending" and "kyc" in statement:
            owner = "Compliance / Operations"

        if lending_model == "Partner-led" and ("partner" in statement or "csp" in statement):
            owner = "Vendor Management / Compliance"

        rows.append(
            {
                "company_name": company_name,
                "sector": sector,
                "business_type": business_type,
                "control_id": c.get("control_id", ""),
                "statement": c.get("statement", ""),
                "category": c.get("category", ""),
                "severity": c.get("severity", ""),
                "control_type": c.get("control_type", ""),
                "applicability": applicability,
                "applicability_reason": reason,
                "owner": owner,
                "status": "Not Assessed",
                "evidence_type": c.get("evidence_type", "Documentary Evidence"),
                "evidence_link": "",
                "last_review_date": "",
                "next_review_date": "",
                "source_doc_title": c.get("doc_title", ""),
                "source_page": c.get("page", ""),
            }
        )

    save_company_controls(rows)
    return rows

# ----------------------------
# UPDATE COMPANY CONTROL
# ----------------------------

def update_company_control(control_id: str, updates: dict) -> bool:
    rows = load_company_controls()
    updated = False

    for row in rows:
        if row.get("control_id") == control_id:
            row.update(updates)
            updated = True
            break

    if updated:
        save_company_controls(rows)

    return updated


# ----------------------------
# COMPLIANCE SUMMARY
# ----------------------------

def get_company_control_summary():
    rows = load_company_controls()

    total = len(rows)

    by_status = {
        "Not Assessed": 0,
        "In Progress": 0,
        "Implemented": 0,
        "Not Applicable": 0,
    }

    high_risk_open = 0

    for row in rows:
        status = row.get("status", "Not Assessed")

        if status not in by_status:
            by_status[status] = 0

        by_status[status] += 1

        severity = (row.get("severity") or "").lower()

        if severity == "high" and status != "Implemented":
            high_risk_open += 1

    return {
        "total_controls": total,
        "status_breakdown": by_status,
        "high_risk_open": high_risk_open,
    }