"""Compatibility wrapper for the legacy LLM module path.

The real LLM implementation now lives under ``services.llm``. This module keeps
the old import path working during migration so current startup and workflows do
not break while callers move to the new service layer.
"""

import os
from typing import Any, Dict, Optional

from services.llm.client import llm_json as service_llm_json
from services.llm.client import ollama_chat as service_ollama_chat
from services.llm.parser import parse_json_response
from services.llm.router import resolve_model


DEFAULT_LLM_MODEL = os.getenv("DEFAULT_LLM_MODEL", "").strip()
CONTROL_CLASSIFIER_MODEL = os.getenv("CONTROL_CLASSIFIER_MODEL", "").strip()
GAP_ANALYSIS_MODEL = os.getenv("GAP_ANALYSIS_MODEL", "").strip()
POLICY_GENERATION_MODEL = os.getenv("POLICY_GENERATION_MODEL", "").strip()


def _json_loads_loose(s: str) -> Dict[str, Any]:
    """Legacy helper retained for compatibility with the previous module API."""
    return parse_json_response(s)


def ollama_chat(
    prompt: str,
    model: Optional[str] = None,
    temperature: float = 0.1,
    purpose: str = "default",
    timeout: Optional[float] = None,
    max_retries: Optional[int] = None,
) -> str:
    """Compatibility wrapper around the new service-layer LLM client."""
    return service_ollama_chat(
        prompt=prompt,
        model=model,
        temperature=temperature,
        purpose=purpose,
        timeout=timeout,
        max_retries=max_retries,
    )


def llm_json(
    prompt: str,
    model: Optional[str] = None,
    temperature: float = 0.1,
    purpose: str = "default",
    timeout: Optional[float] = None,
    max_retries: Optional[int] = None,
) -> Dict[str, Any]:
    """Compatibility wrapper that preserves the previous structured-response API."""
    return service_llm_json(
        prompt=prompt,
        model=model,
        temperature=temperature,
        purpose=purpose,
        timeout=timeout,
        max_retries=max_retries,
    )
