"""Startup health checks and local auto-launch helpers for Ollama.

This module lets the Streamlit shell detect whether the configured local Ollama
endpoint is reachable, optionally launch the macOS app once, and provide a
clear user-facing status before a workflow fails deep in generation.
"""

from __future__ import annotations

import platform
import subprocess
import time
from typing import Any, Dict, Iterable, List
from urllib.parse import urlparse

import requests

from services.llm.router import resolve_model


DEFAULT_HEALTH_TIMEOUT_SECONDS = 2.0
DEFAULT_AUTOSTART_WAIT_SECONDS = 6.0
DEFAULT_POLL_INTERVAL_SECONDS = 0.5


def _base_url(api_url: str) -> str:
    parsed = urlparse(api_url)
    if not parsed.scheme or not parsed.netloc:
        return "http://localhost:11434"
    return f"{parsed.scheme}://{parsed.netloc}"


def _health_url(api_url: str) -> str:
    return f"{_base_url(api_url).rstrip('/')}/api/tags"


def _is_local_ollama_url(api_url: str) -> bool:
    parsed = urlparse(api_url)
    host = (parsed.hostname or "").strip().lower()
    return host in {"127.0.0.1", "localhost"}


def _available_model_names(payload: Dict[str, Any]) -> List[str]:
    models = payload.get("models", [])
    if not isinstance(models, list):
        return []

    names: List[str] = []
    for item in models:
        if not isinstance(item, dict):
            continue
        name = str(item.get("name", "") or "").strip()
        if name:
            names.append(name)
    return names


def _resolve_required_models(purposes: Iterable[str]) -> Dict[str, str]:
    models: Dict[str, str] = {}
    for purpose in purposes:
        models[str(purpose)] = resolve_model(purpose=purpose)
    return models


def check_ollama_health(
    api_url: str,
    purposes: Iterable[str] | None = None,
    timeout_seconds: float = DEFAULT_HEALTH_TIMEOUT_SECONDS,
) -> Dict[str, Any]:
    """Check whether Ollama is reachable and whether required models exist."""

    purposes = list(purposes or ["default"])
    required_models = _resolve_required_models(purposes)
    unique_required_models = sorted({model for model in required_models.values() if str(model).strip()})
    health_url = _health_url(api_url)

    try:
        response = requests.get(health_url, timeout=timeout_seconds)
        response.raise_for_status()
        payload = response.json()
    except Exception as exc:
        return {
            "ok": False,
            "api_url": api_url,
            "health_url": health_url,
            "configured_model": required_models.get("default", ""),
            "required_models": required_models,
            "missing_models": unique_required_models,
            "model_available": False,
            "available_models": [],
            "message": f"Ollama is not reachable at {health_url}: {type(exc).__name__}: {exc}",
        }

    available_models = _available_model_names(payload)
    missing_models = [model for model in unique_required_models if model not in available_models]
    model_available = not missing_models

    if missing_models:
        return {
            "ok": False,
            "api_url": api_url,
            "health_url": health_url,
            "configured_model": required_models.get("default", ""),
            "required_models": required_models,
            "missing_models": missing_models,
            "model_available": False,
            "available_models": available_models,
            "message": (
                "Ollama is running, but one or more configured models are missing: "
                + ", ".join(missing_models)
            ),
        }

    return {
        "ok": True,
        "api_url": api_url,
        "health_url": health_url,
        "configured_model": required_models.get("default", ""),
        "required_models": required_models,
        "missing_models": [],
        "model_available": True,
        "available_models": available_models,
        "message": "Ollama is ready. All configured workflow models are available.",
    }


def autostart_ollama(
    api_url: str,
    wait_seconds: float = DEFAULT_AUTOSTART_WAIT_SECONDS,
    poll_interval_seconds: float = DEFAULT_POLL_INTERVAL_SECONDS,
) -> Dict[str, Any]:
    """Attempt to launch local Ollama once on supported desktop environments."""

    system_name = platform.system().lower()
    if not _is_local_ollama_url(api_url):
        return {
            "attempted": False,
            "supported": False,
            "launched": False,
            "message": "Auto-start is only supported for a local Ollama URL.",
        }

    if system_name != "darwin":
        return {
            "attempted": False,
            "supported": False,
            "launched": False,
            "message": "Auto-start is currently implemented only for macOS.",
        }

    try:
        subprocess.Popen(
            ["open", "-a", "Ollama"],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
    except Exception as exc:
        return {
            "attempted": True,
            "supported": True,
            "launched": False,
            "message": f"Failed to launch Ollama.app automatically: {type(exc).__name__}: {exc}",
        }

    deadline = time.time() + max(wait_seconds, 0.0)
    health_url = _health_url(api_url)
    while time.time() < deadline:
        try:
            response = requests.get(health_url, timeout=DEFAULT_HEALTH_TIMEOUT_SECONDS)
            if response.ok:
                return {
                    "attempted": True,
                    "supported": True,
                    "launched": True,
                    "message": "Ollama.app was launched automatically.",
                }
        except Exception:
            pass

        time.sleep(max(poll_interval_seconds, 0.1))

    return {
        "attempted": True,
        "supported": True,
        "launched": False,
        "message": "Tried to launch Ollama.app, but it did not become reachable in time.",
    }


def ensure_ollama_ready(
    api_url: str,
    purposes: Iterable[str] | None = None,
    allow_autostart: bool = True,
) -> Dict[str, Any]:
    """Check Ollama health and optionally try a one-time local auto-start."""

    initial = check_ollama_health(api_url=api_url, purposes=purposes)
    if initial["ok"] or not allow_autostart:
        initial["autostart_attempted"] = False
        initial["autostart_message"] = ""
        return initial

    autostart_result = autostart_ollama(api_url=api_url)
    if not autostart_result.get("attempted"):
        initial["autostart_attempted"] = False
        initial["autostart_message"] = autostart_result.get("message", "")
        return initial

    post_launch = check_ollama_health(api_url=api_url, purposes=purposes)
    post_launch["autostart_attempted"] = True
    post_launch["autostart_message"] = autostart_result.get("message", "")
    return post_launch


def default_ollama_api_url() -> str:
    """Return the configured Ollama API URL used by the LLM client."""

    from services.llm.client import DEFAULT_OLLAMA_URL

    return DEFAULT_OLLAMA_URL
