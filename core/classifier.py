import json
import hashlib
from pathlib import Path
from typing import Dict, Any

from configs.control_taxonomy import (
    apply_control_override,
    list_control_overrides as _list_control_overrides,
    load_control_taxonomy,
    make_control_lookup_key,
    normalize_classification,
    save_control_override as _save_control_override,
    delete_control_override as _delete_control_override,
    taxonomy_fingerprint,
)
from services.llm.client import llm_json

CACHE_PATH = Path("data/cache/control_classification_cache.json")


def _load_cache() -> Dict[str, Any]:
    if not CACHE_PATH.exists():
        return {}
    with open(CACHE_PATH, "r", encoding="utf-8") as f:
        return json.load(f)


def _save_cache(cache: Dict[str, Any]) -> None:
    CACHE_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(CACHE_PATH, "w", encoding="utf-8") as f:
        json.dump(cache, f, ensure_ascii=False, indent=2)


def _make_cache_key(control_text: str, model: str, taxonomy: Dict[str, Any]) -> str:
    """Create a stable cache key that changes when the model or taxonomy changes."""

    payload = {
        "control_lookup_key": make_control_lookup_key(control_text),
        "model": str(model or "").strip(),
        "taxonomy_fingerprint": taxonomy_fingerprint(taxonomy),
    }
    encoded = json.dumps(payload, ensure_ascii=False, sort_keys=True).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def build_classification_prompt(control_text: str, taxonomy: Dict[str, Any]) -> str:
    fields = taxonomy.get("fields", {})
    control_type_allowed = fields.get("control_type", {}).get("allowed", [])
    severity_allowed = fields.get("severity", {}).get("allowed", [])
    category_allowed = fields.get("category", {}).get("allowed", [])
    category_allow_custom = bool(fields.get("category", {}).get("allow_custom"))

    category_guidance = f"- preferred category values: {category_allowed}\n" if category_allowed else ""
    if category_allow_custom:
        category_guidance += "- if no preferred category fits, use a short custom label\n"

    return f"""
You are classifying a regulatory control for a compliance product.

Return ONLY valid JSON with these keys:
{{
  "category": "",
  "control_type": "",
  "severity": "",
  "policy_tags": [],
  "implementation_hint": ""
}}

Allowed values:
- control_type: {control_type_allowed}
- severity: {severity_allowed}

Control:
\"\"\"{control_text}\"\"\"

Rules:
- category should be concise
{category_guidance}- do not invent values outside the allowed control_type or severity lists
- policy_tags should be likely policy document names
- implementation_hint should be practical and short
"""


def classify_control(control_text: str, model: str = "qwen2.5:3b") -> Dict[str, Any]:
    taxonomy = load_control_taxonomy()
    cache = _load_cache()
    key = _make_cache_key(control_text, model=model, taxonomy=taxonomy)

    if key in cache:
        return apply_control_override(control_text, cache[key])

    data = llm_json(
        build_classification_prompt(control_text, taxonomy),
        model=model,
        purpose="control_classifier",
    )

    result = normalize_classification(data, taxonomy)

    cache[key] = result
    _save_cache(cache)

    return apply_control_override(control_text, result)


def save_classification_override(
    control_text: str,
    updates: Dict[str, Any],
    *,
    source: str = "user_feedback",
    note: str = "",
    updated_by: str = "",
) -> Dict[str, Any]:
    """Persist a user correction for a control's classification."""

    return _save_control_override(
        control_text,
        updates,
        source=source,
        note=note,
        updated_by=updated_by,
    )


def list_classification_overrides() -> list[Dict[str, Any]]:
    """List saved user correction entries."""

    return _list_control_overrides()


def delete_classification_override(control_text: str) -> bool:
    """Delete a saved user correction entry."""

    return _delete_control_override(control_text)
