"""Workflow helpers for the control-classification admin page."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List

from configs.control_taxonomy import (
    DEFAULT_OVERRIDES_PATH,
    DEFAULT_TAXONOMY_PATH,
    build_default_control_taxonomy,
    load_control_taxonomy,
    reset_control_taxonomy,
    save_control_taxonomy,
)
from core.classifier import (
    delete_classification_override,
    list_classification_overrides,
    save_classification_override,
)
from core.control_registry import load_controls_master


def _statement_preview(text: str, max_len: int = 100) -> str:
    """Return a compact single-line preview for control statements."""

    cleaned = " ".join(str(text or "").split())
    if len(cleaned) <= max_len:
        return cleaned
    return cleaned[: max_len - 3].rstrip() + "..."


def get_classification_admin_page_data() -> Dict[str, Any]:
    """Load all data required to review and edit taxonomy and overrides."""

    taxonomy = load_control_taxonomy()
    overrides = list_classification_overrides()
    master_rows = load_controls_master()

    selectable_controls: List[Dict[str, Any]] = []
    for row in master_rows:
        statement = str(row.get("statement", "")).strip()
        control_id = str(row.get("control_id", "")).strip()
        label = f"{control_id or 'No ID'} | {_statement_preview(statement)}"
        selectable_controls.append(
            {
                "label": label,
                "control_id": control_id,
                "statement": statement,
                "category": row.get("category", ""),
                "control_type": row.get("control_type", ""),
                "severity": row.get("severity", ""),
                "policy_tags": row.get("policy_tags", []),
                "implementation_hint": row.get("implementation_hint", ""),
            }
        )

    return {
        "taxonomy": taxonomy,
        "default_taxonomy": build_default_control_taxonomy(),
        "taxonomy_json": json.dumps(taxonomy, ensure_ascii=False, indent=2),
        "taxonomy_path": str(DEFAULT_TAXONOMY_PATH),
        "overrides": overrides,
        "overrides_path": str(DEFAULT_OVERRIDES_PATH),
        "master_rows": master_rows,
        "selectable_controls": selectable_controls,
        "summary": {
            "topic_rule_count": len(taxonomy.get("topic", {}).get("rules", [])),
            "override_count": len(overrides),
            "master_control_count": len(master_rows),
        },
    }


def save_taxonomy_from_text(raw_text: str) -> Dict[str, Any]:
    """Parse and persist a taxonomy JSON document from the admin editor."""

    parsed = json.loads(str(raw_text or "").strip() or "{}")
    saved = save_control_taxonomy(parsed)
    return {
        "saved": True,
        "taxonomy": saved,
        "taxonomy_json": json.dumps(saved, ensure_ascii=False, indent=2),
        "path": str(DEFAULT_TAXONOMY_PATH),
    }


def reset_taxonomy_to_default() -> Dict[str, Any]:
    """Reset the external taxonomy config to the built-in defaults."""

    saved = reset_control_taxonomy()
    return {
        "saved": True,
        "taxonomy": saved,
        "taxonomy_json": json.dumps(saved, ensure_ascii=False, indent=2),
        "path": str(DEFAULT_TAXONOMY_PATH),
    }


def build_override_rows(overrides: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Flatten override entries for simple table display."""

    rows: List[Dict[str, Any]] = []
    for entry in overrides:
        override_payload = entry.get("overrides", {}) or {}
        metadata = entry.get("metadata", {}) or {}
        rows.append(
            {
                "lookup_key": entry.get("lookup_key", ""),
                "control_text": entry.get("control_text", ""),
                "category": override_payload.get("category", ""),
                "control_type": override_payload.get("control_type", ""),
                "severity": override_payload.get("severity", ""),
                "policy_tags": ", ".join(override_payload.get("policy_tags", []))
                if isinstance(override_payload.get("policy_tags"), list)
                else override_payload.get("policy_tags", ""),
                "implementation_hint": override_payload.get("implementation_hint", ""),
                "source": metadata.get("source", ""),
                "updated_by": metadata.get("updated_by", ""),
                "updated_at": metadata.get("updated_at", ""),
                "note": metadata.get("note", ""),
            }
        )
    return rows


def save_override_from_form(
    control_text: str,
    category: str,
    control_type: str,
    severity: str,
    policy_tags_text: str,
    implementation_hint: str,
    note: str = "",
    updated_by: str = "",
    source: str = "user_feedback",
) -> Dict[str, Any]:
    """Persist one user correction entry from admin-form inputs."""

    tags = [item.strip() for item in str(policy_tags_text or "").replace(",", ";").split(";") if item.strip()]
    updates = {
        "category": category,
        "control_type": control_type,
        "severity": severity,
        "policy_tags": tags,
        "implementation_hint": implementation_hint,
    }

    entry = save_classification_override(
        control_text=control_text,
        updates=updates,
        source=source,
        note=note,
        updated_by=updated_by,
    )

    return {
        "saved": True,
        "entry": entry,
    }


def delete_override_for_control(control_text: str) -> Dict[str, Any]:
    """Delete one saved override by control statement."""

    deleted = delete_classification_override(control_text)
    return {
        "deleted": deleted,
    }


def load_override_entry_for_control(control_text: str) -> Dict[str, Any]:
    """Return the override entry that matches the given statement, if any."""

    normalized = str(control_text or "").strip()
    for entry in list_classification_overrides():
        if str(entry.get("control_text", "")).strip() == normalized:
            return entry
    return {}
