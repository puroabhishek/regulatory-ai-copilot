import json
import os
from pathlib import Path
from typing import Dict, Any, Optional

import requests
from dotenv import load_dotenv


ROOT_DIR = Path(__file__).resolve().parent.parent
load_dotenv(dotenv_path=ROOT_DIR / ".env")


DEFAULT_LLM_MODEL = os.getenv("DEFAULT_LLM_MODEL", "").strip()
CONTROL_CLASSIFIER_MODEL = os.getenv("CONTROL_CLASSIFIER_MODEL", "").strip()
GAP_ANALYSIS_MODEL = os.getenv("GAP_ANALYSIS_MODEL", "").strip()
POLICY_GENERATION_MODEL = os.getenv("POLICY_GENERATION_MODEL", "").strip()


def resolve_model(purpose: str = "default", override: Optional[str] = None) -> str:
    """
    Resolve the model from:
    1. explicit override
    2. purpose-specific env var
    3. default env var
    """
    if override and str(override).strip():
        return str(override).strip()

    purpose_map = {
        "control_classifier": CONTROL_CLASSIFIER_MODEL,
        "gap_analysis": GAP_ANALYSIS_MODEL,
        "policy_generation": POLICY_GENERATION_MODEL,
        "default": DEFAULT_LLM_MODEL,
    }

    resolved = purpose_map.get(purpose) or DEFAULT_LLM_MODEL
    resolved = str(resolved or "").strip()

    if not resolved:
        raise ValueError(
            f"No LLM model configured for purpose='{purpose}'. "
            "Set the appropriate value in .env, for example DEFAULT_LLM_MODEL or GAP_ANALYSIS_MODEL."
        )

    return resolved


def _json_loads_loose(s: str) -> Dict[str, Any]:
    s = str(s or "").strip()

    if not s:
        raise ValueError("Model returned empty output.")

    try:
        return json.loads(s)
    except Exception:
        pass

    start = s.find("{")
    end = s.rfind("}")
    if start != -1 and end != -1 and end > start:
        return json.loads(s[start : end + 1])

    raise ValueError("Model did not return valid JSON.")


def ollama_chat(
    prompt: str,
    model: Optional[str] = None,
    temperature: float = 0.1,
    purpose: str = "default",
) -> str:
    url = "http://localhost:11434/api/chat"
    resolved_model = resolve_model(purpose=purpose, override=model)

    payload = {
        "model": resolved_model,
        "messages": [{"role": "user", "content": prompt}],
        "options": {"temperature": temperature},
        "stream": False,
    }

    try:
        response = requests.post(url, json=payload, timeout=600)
    except requests.RequestException as e:
        raise RuntimeError(f"Failed to connect to Ollama at {url}: {type(e).__name__}: {e}") from e

    if not response.ok:
        raise RuntimeError(
            f"Ollama error {response.status_code} for model '{resolved_model}': {response.text}"
        )

    try:
        data = response.json()
    except Exception as e:
        raise ValueError(f"Failed to parse Ollama response as JSON: {response.text}") from e

    message = data.get("message", {})
    content = message.get("content", "")

    if not content:
        raise ValueError(f"Ollama returned empty message content: {data}")

    return content


def llm_json(
    prompt: str,
    model: Optional[str] = None,
    temperature: float = 0.1,
    purpose: str = "default",
) -> Dict[str, Any]:
    output = ollama_chat(
        prompt=prompt,
        model=model,
        temperature=temperature,
        purpose=purpose,
    )
    return _json_loads_loose(output)