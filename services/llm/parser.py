"""Parsing helpers for structured LLM responses.

This module keeps defensive JSON parsing out of business logic so callers can
rely on a single place for:
- empty-response checks
- fenced-code-block cleanup
- loose extraction of JSON objects from mixed text output
"""

import json
from typing import Any, Dict, Optional


def _strip_code_fence(content: str) -> str:
    text = str(content or "").strip()

    if not text.startswith("```"):
        return text

    lines = text.splitlines()
    if not lines:
        return text

    if lines[0].startswith("```"):
        lines = lines[1:]
    if lines and lines[-1].strip() == "```":
        lines = lines[:-1]

    return "\n".join(lines).strip()


def _extract_json_object(content: str) -> Optional[str]:
    text = _strip_code_fence(content)

    start = text.find("{")
    end = text.rfind("}")

    if start == -1 or end == -1 or end <= start:
        return None

    return text[start : end + 1]


def safe_json_loads(content: str) -> Any:
    """Parse JSON with a few safe fallbacks for model output formatting."""
    text = str(content or "").strip()
    if not text:
        raise ValueError("Model returned empty output.")

    cleaned = _strip_code_fence(text)
    try:
        return json.loads(cleaned)
    except Exception:
        pass

    candidate = _extract_json_object(cleaned)
    if candidate is None:
        raise ValueError("Model did not return valid JSON.")

    try:
        return json.loads(candidate)
    except Exception as exc:
        raise ValueError("Model did not return valid JSON.") from exc


def parse_json_response(content: str) -> Dict[str, Any]:
    """Parse a model response and require a top-level JSON object."""
    data = safe_json_loads(content)

    if not isinstance(data, dict):
        raise ValueError(f"Expected a JSON object from the model, got {type(data).__name__}.")

    return data
