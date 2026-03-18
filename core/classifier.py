import json
import hashlib
from pathlib import Path
from typing import Dict, Any

from core.llm import llm_json

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


def _make_key(control_text: str) -> str:
    """
    What it does:
    - Creates a stable hash key from the control text.
    Why:
    - Long control text is awkward as a raw dictionary key.
    """
    return hashlib.sha256(control_text.strip().lower().encode("utf-8")).hexdigest()


def build_classification_prompt(control_text: str) -> str:
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
- control_type: ["Technical", "Operational", "Governance", "Legal"]
- severity: ["High", "Medium", "Low"]

Control:
\"\"\"{control_text}\"\"\"

Rules:
- category should be concise
- policy_tags should be likely policy document names
- implementation_hint should be practical and short
"""


def classify_control(control_text: str, model: str = "qwen2.5:3b") -> Dict[str, Any]:
    cache = _load_cache()
    key = _make_key(control_text)

    if key in cache:
        return cache[key]

    data = llm_json(build_classification_prompt(control_text), model=model)

    result = {
        "category": str(data.get("category", "")).strip(),
        "control_type": str(data.get("control_type", "")).strip(),
        "severity": str(data.get("severity", "")).strip(),
        "policy_tags": data.get("policy_tags", []) if isinstance(data.get("policy_tags", []), list) else [],
        "implementation_hint": str(data.get("implementation_hint", "")).strip(),
    }

    cache[key] = result
    _save_cache(cache)

    return result