"""Helpers for external control taxonomy and user classification overrides."""

from __future__ import annotations

import hashlib
import json
from copy import deepcopy
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional


DEFAULT_TAXONOMY_PATH = Path(__file__).resolve().with_name("control_taxonomy.json")
DEFAULT_OVERRIDES_PATH = Path(__file__).resolve().parent.parent / "data" / "control_classification_overrides.json"

CLASSIFICATION_FIELDS = (
    "category",
    "control_type",
    "severity",
    "policy_tags",
    "implementation_hint",
)

DEFAULT_CLASSIFICATION = {
    "category": "",
    "control_type": "",
    "severity": "",
    "policy_tags": [],
    "implementation_hint": "",
}


def _default_taxonomy() -> Dict[str, Any]:
    """Return the built-in taxonomy used when the config file is unavailable."""

    return {
        "version": "default",
        "modality": {
            "priority": ["must", "shall", "should", "may"],
        },
        "topic": {
            "default": "General",
            "rules": [
                {"label": "Regulatory Approval", "keywords": ["approval", "qcb"]},
                {"label": "Register & Reporting", "keywords": ["register", "inventory", "disclose"]},
                {"label": "Assurance & Audit", "keywords": ["audit", "soc"]},
                {"label": "Security Testing", "keywords": ["test", "penetration", "vulnerability"]},
                {"label": "Security Controls", "keywords": ["encrypt", "authentication", "access"]},
                {"label": "Data Protection", "keywords": ["confidential", "privacy", "personal data"]},
                {"label": "Data Residency", "keywords": ["pii", "within qatar"]},
                {"label": "Outsourcing & Vendor Risk", "keywords": ["outsourcing", "csp"]},
                {"label": "Risk Management", "keywords": ["risk"]},
                {"label": "Governance", "keywords": ["governance", "board", "strategy"]},
                {"label": "Resilience & BCP", "keywords": ["business continuity", "resilien"]},
            ],
        },
        "fields": {
            "category": {
                "default": "",
                "allow_custom": True,
                "allowed": [
                    "Governance",
                    "Operational",
                    "Technical",
                    "Legal",
                    "Data Protection",
                    "Data Handling",
                    "Risk Management",
                    "Retention",
                    "Register & Reporting",
                    "Regulatory Approval",
                    "Assurance & Audit",
                    "Security Controls",
                    "Security Testing",
                    "Data Residency",
                    "Outsourcing & Vendor Risk",
                    "Resilience & BCP",
                    "General",
                ],
                "aliases": {
                    "data governance": "Governance",
                    "compliance": "Governance",
                },
            },
            "control_type": {
                "default": "",
                "allowed": ["Technical", "Operational", "Governance", "Legal"],
                "aliases": {
                    "implementation": "Operational",
                    "sub scope implementation": "Operational",
                    "identification": "Operational",
                    "physical access management": "Operational",
                },
            },
            "severity": {
                "default": "",
                "allowed": ["High", "Medium", "Low"],
                "aliases": {
                    "critical": "High",
                    "moderate": "Medium",
                    "minor": "Low",
                },
            },
        },
    }


def build_default_control_taxonomy() -> Dict[str, Any]:
    """Return the default taxonomy payload for reset or first-run flows."""

    return deepcopy(_default_taxonomy())


def _merge_dicts(base: Dict[str, Any], override: Dict[str, Any]) -> Dict[str, Any]:
    """Recursively merge two dictionaries."""

    merged = deepcopy(base)
    for key, value in override.items():
        if isinstance(value, dict) and isinstance(merged.get(key), dict):
            merged[key] = _merge_dicts(merged[key], value)
        else:
            merged[key] = value
    return merged


def _read_json(path: Path, fallback: Any) -> Any:
    """Load a JSON file, falling back to a default value when needed."""

    if not path.exists():
        return deepcopy(fallback)

    try:
        with open(path, "r", encoding="utf-8") as handle:
            return json.load(handle)
    except (OSError, json.JSONDecodeError):
        return deepcopy(fallback)


def _write_json(path: Path, data: Any) -> None:
    """Write JSON atomically so manual edits and app writes do not interleave badly."""

    path.parent.mkdir(parents=True, exist_ok=True)
    temp_path = path.with_suffix(path.suffix + ".tmp")

    with open(temp_path, "w", encoding="utf-8") as handle:
        json.dump(data, handle, ensure_ascii=False, indent=2)

    temp_path.replace(path)


def make_control_lookup_key(control_text: str) -> str:
    """Create a stable hash for a control statement."""

    normalized = str(control_text or "").strip().lower()
    return hashlib.sha256(normalized.encode("utf-8")).hexdigest()


def load_control_taxonomy(path: Optional[Path] = None) -> Dict[str, Any]:
    """Load the editable control taxonomy config."""

    base = build_default_control_taxonomy()
    taxonomy_path = path or DEFAULT_TAXONOMY_PATH
    loaded = _read_json(taxonomy_path, base)

    if not isinstance(loaded, dict):
        return base

    return _merge_dicts(base, loaded)


def save_control_taxonomy(data: Dict[str, Any], path: Optional[Path] = None) -> Dict[str, Any]:
    """Persist a taxonomy config after merging it with defaults."""

    if not isinstance(data, dict):
        raise ValueError("Control taxonomy must be a JSON object.")

    taxonomy_path = path or DEFAULT_TAXONOMY_PATH
    merged = _merge_dicts(build_default_control_taxonomy(), data)
    _write_json(taxonomy_path, merged)
    return merged


def reset_control_taxonomy(path: Optional[Path] = None) -> Dict[str, Any]:
    """Reset the saved taxonomy config back to the built-in defaults."""

    default_taxonomy = build_default_control_taxonomy()
    taxonomy_path = path or DEFAULT_TAXONOMY_PATH
    _write_json(taxonomy_path, default_taxonomy)
    return default_taxonomy


def taxonomy_fingerprint(taxonomy: Dict[str, Any]) -> str:
    """Return a stable hash for the current taxonomy contents."""

    payload = json.dumps(taxonomy, ensure_ascii=False, sort_keys=True)
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def get_modality_priority(path: Optional[Path] = None) -> List[str]:
    """Return the modality detection priority from the external taxonomy."""

    taxonomy = load_control_taxonomy(path)
    priority = taxonomy.get("modality", {}).get("priority", [])
    if not isinstance(priority, list):
        return []

    return [str(item).strip().lower() for item in priority if str(item).strip()]


def get_topic_rules(path: Optional[Path] = None) -> List[Dict[str, Any]]:
    """Return the configured topic rules."""

    taxonomy = load_control_taxonomy(path)
    rules = taxonomy.get("topic", {}).get("rules", [])
    if not isinstance(rules, list):
        return []

    cleaned: List[Dict[str, Any]] = []
    for rule in rules:
        if not isinstance(rule, dict):
            continue

        label = str(rule.get("label", "")).strip()
        keywords = rule.get("keywords", [])

        if not label or not isinstance(keywords, list):
            continue

        cleaned.append(
            {
                "label": label,
                "keywords": [str(keyword).strip().lower() for keyword in keywords if str(keyword).strip()],
            }
        )

    return cleaned


def get_topic_default(path: Optional[Path] = None) -> str:
    """Return the configured default topic label."""

    taxonomy = load_control_taxonomy(path)
    return str(taxonomy.get("topic", {}).get("default", "General")).strip() or "General"


def _field_config(field_name: str, taxonomy: Dict[str, Any]) -> Dict[str, Any]:
    """Return the config block for a classification field."""

    fields = taxonomy.get("fields", {})
    field_config = fields.get(field_name, {})
    return field_config if isinstance(field_config, dict) else {}


def normalize_policy_tags(value: Any) -> List[str]:
    """Normalize policy tags into a de-duplicated list."""

    raw_items: List[str] = []

    if isinstance(value, list):
        raw_items = [str(item).strip() for item in value if str(item).strip()]
    elif value is not None and value != "":
        text = str(value).strip()
        splitter = ";" if ";" in text else ","
        raw_items = [part.strip() for part in text.split(splitter)] if splitter in text else [text]

    seen = set()
    normalized: List[str] = []
    for item in raw_items:
        if item.lower() in seen:
            continue
        seen.add(item.lower())
        normalized.append(item)

    return normalized


def normalize_classification_value(field_name: str, value: Any, taxonomy: Dict[str, Any]) -> Any:
    """Normalize a single classification field using the external taxonomy."""

    if field_name == "policy_tags":
        return normalize_policy_tags(value)

    if field_name == "implementation_hint":
        return str(value or "").strip()

    field_config = _field_config(field_name, taxonomy)
    default_value = field_config.get("default", "")
    raw_value = str(value or "").strip()

    if not raw_value:
        return default_value

    allowed = field_config.get("allowed", [])
    aliases = field_config.get("aliases", {})
    allow_custom = bool(field_config.get("allow_custom"))

    allowed_map = {str(item).strip().lower(): str(item).strip() for item in allowed if str(item).strip()}
    alias_map = {str(key).strip().lower(): str(val).strip() for key, val in aliases.items() if str(key).strip() and str(val).strip()}

    canonical = alias_map.get(raw_value.lower(), raw_value)

    if canonical.lower() in allowed_map:
        return allowed_map[canonical.lower()]
    if allow_custom:
        return canonical
    return default_value


def normalize_classification(data: Optional[Dict[str, Any]], taxonomy: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """Normalize a full classification payload."""

    source = data if isinstance(data, dict) else {}
    active_taxonomy = taxonomy or load_control_taxonomy()

    return {
        "category": normalize_classification_value("category", source.get("category", ""), active_taxonomy),
        "control_type": normalize_classification_value("control_type", source.get("control_type", ""), active_taxonomy),
        "severity": normalize_classification_value("severity", source.get("severity", ""), active_taxonomy),
        "policy_tags": normalize_classification_value("policy_tags", source.get("policy_tags", []), active_taxonomy),
        "implementation_hint": normalize_classification_value("implementation_hint", source.get("implementation_hint", ""), active_taxonomy),
    }


def normalize_override_updates(updates: Optional[Dict[str, Any]], taxonomy: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """Normalize only the explicitly provided override fields."""

    source = updates if isinstance(updates, dict) else {}
    active_taxonomy = taxonomy or load_control_taxonomy()
    normalized: Dict[str, Any] = {}

    for field_name in CLASSIFICATION_FIELDS:
        if field_name not in source:
            continue
        normalized[field_name] = normalize_classification_value(field_name, source.get(field_name), active_taxonomy)

    return normalized


def load_control_overrides(
    path: Optional[Path] = None,
    taxonomy_path: Optional[Path] = None,
) -> Dict[str, Dict[str, Any]]:
    """Load the file-backed user correction store."""

    overrides_path = path or DEFAULT_OVERRIDES_PATH
    raw = _read_json(overrides_path, {})
    if not isinstance(raw, dict):
        return {}

    taxonomy = load_control_taxonomy(taxonomy_path)
    cleaned: Dict[str, Dict[str, Any]] = {}

    for key, entry in raw.items():
        if not isinstance(entry, dict):
            continue

        if isinstance(entry.get("overrides"), dict):
            override_payload = entry.get("overrides", {})
        elif isinstance(entry.get("classification"), dict):
            override_payload = entry.get("classification", {})
        else:
            override_payload = {field: entry.get(field) for field in CLASSIFICATION_FIELDS if field in entry}

        metadata = entry.get("metadata", {})
        if not isinstance(metadata, dict):
            metadata = {}

        cleaned[str(key)] = {
            "control_text": str(entry.get("control_text", "")).strip(),
            "overrides": normalize_override_updates(override_payload, taxonomy),
            "metadata": {str(k): str(v) for k, v in metadata.items() if str(v).strip()},
        }

    return cleaned


def get_control_override(
    control_text: str,
    path: Optional[Path] = None,
    taxonomy_path: Optional[Path] = None,
) -> Dict[str, Any]:
    """Return any saved override payload for a control statement."""

    overrides = load_control_overrides(path=path, taxonomy_path=taxonomy_path)
    entry = overrides.get(make_control_lookup_key(control_text), {})
    return dict(entry.get("overrides", {})) if isinstance(entry, dict) else {}


def apply_control_override(
    control_text: str,
    classification: Optional[Dict[str, Any]],
    path: Optional[Path] = None,
    taxonomy_path: Optional[Path] = None,
) -> Dict[str, Any]:
    """Overlay user corrections on top of normalized model output."""

    taxonomy = load_control_taxonomy(taxonomy_path)
    merged = normalize_classification(classification, taxonomy)
    override_payload = get_control_override(control_text, path=path, taxonomy_path=taxonomy_path)

    if not override_payload:
        return merged

    merged.update(override_payload)
    return normalize_classification(merged, taxonomy)


def save_control_override(
    control_text: str,
    updates: Optional[Dict[str, Any]],
    *,
    source: str = "user_feedback",
    note: str = "",
    updated_by: str = "",
    path: Optional[Path] = None,
    taxonomy_path: Optional[Path] = None,
) -> Dict[str, Any]:
    """Persist user corrections without changing the source code or taxonomy module."""

    taxonomy = load_control_taxonomy(taxonomy_path)
    overrides_path = path or DEFAULT_OVERRIDES_PATH
    overrides = load_control_overrides(path=overrides_path, taxonomy_path=taxonomy_path)

    lookup_key = make_control_lookup_key(control_text)
    existing = overrides.get(lookup_key, {})
    merged_updates = dict(existing.get("overrides", {}))
    merged_updates.update(normalize_override_updates(updates, taxonomy))

    metadata = dict(existing.get("metadata", {}))
    metadata["source"] = str(source or metadata.get("source", "user_feedback")).strip() or "user_feedback"
    metadata["updated_at"] = datetime.now(timezone.utc).isoformat()

    if note:
        metadata["note"] = str(note).strip()
    if updated_by:
        metadata["updated_by"] = str(updated_by).strip()

    entry = {
        "control_text": str(control_text or "").strip(),
        "overrides": merged_updates,
        "metadata": metadata,
    }

    overrides[lookup_key] = entry
    _write_json(overrides_path, overrides)
    return entry


def delete_control_override(control_text: str, path: Optional[Path] = None, taxonomy_path: Optional[Path] = None) -> bool:
    """Remove a saved override for a control statement."""

    overrides_path = path or DEFAULT_OVERRIDES_PATH
    overrides = load_control_overrides(path=overrides_path, taxonomy_path=taxonomy_path)
    lookup_key = make_control_lookup_key(control_text)

    if lookup_key not in overrides:
        return False

    overrides.pop(lookup_key, None)
    _write_json(overrides_path, overrides)
    return True


def list_control_overrides(path: Optional[Path] = None, taxonomy_path: Optional[Path] = None) -> List[Dict[str, Any]]:
    """Return saved override entries in a simple list format."""

    overrides = load_control_overrides(path=path, taxonomy_path=taxonomy_path)
    rows: List[Dict[str, Any]] = []

    for lookup_key, entry in overrides.items():
        rows.append(
            {
                "lookup_key": lookup_key,
                "control_text": entry.get("control_text", ""),
                "overrides": entry.get("overrides", {}),
                "metadata": entry.get("metadata", {}),
            }
        )

    rows.sort(key=lambda row: row.get("metadata", {}).get("updated_at", ""), reverse=True)
    return rows
