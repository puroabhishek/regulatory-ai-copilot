"""LLM request client utilities."""

import hashlib
import os
import time
from dataclasses import dataclass
from typing import Any, Dict, Optional

import requests

from services.llm.parser import parse_json_response
from services.llm.router import resolve_model


def _read_float_env(name: str, default: float) -> float:
    raw = str(os.getenv(name, "")).strip()
    if not raw:
        return default
    try:
        return float(raw)
    except ValueError:
        return default


def _read_int_env(name: str, default: int) -> int:
    raw = str(os.getenv(name, "")).strip()
    if not raw:
        return default
    try:
        return int(raw)
    except ValueError:
        return default


DEFAULT_OLLAMA_URL = os.getenv("OLLAMA_URL", "http://localhost:11434/api/chat").strip() or "http://localhost:11434/api/chat"
DEFAULT_TIMEOUT_SECONDS = _read_float_env("LLM_TIMEOUT_SECONDS", 600.0)
DEFAULT_MAX_RETRIES = max(0, _read_int_env("LLM_MAX_RETRIES", 1))
DEFAULT_RETRY_DELAY_SECONDS = max(0.0, _read_float_env("LLM_RETRY_DELAY_SECONDS", 1.0))


def _response_text(response: requests.Response, fallback: str = "") -> str:
    text = str(getattr(response, "text", "") or fallback).strip()
    return text or "<empty response body>"


def _prompt_hash(prompt: str) -> str:
    return hashlib.sha256(prompt.encode()).hexdigest()[:8]


def _write_audit_log(
    action: str,
    model: str,
    prompt: str,
    duration_ms: int,
    error: Optional[str] = None,
) -> None:
    """Write an audit log entry non-fatally (never raise)."""
    try:
        from services.llm.context import get_llm_context
        from services.db.session import session_scope
        from models.audit_log import AuditLog

        org_id, user_id = get_llm_context()
        with session_scope() as db:
            db.add(AuditLog(
                org_id=org_id,
                user_id=user_id,
                action=action,
                model_used=model,
                prompt_hash=_prompt_hash(prompt),
                duration_ms=duration_ms,
                error=error,
            ))
    except Exception:
        pass


@dataclass
class LLMClient:
    """Thin client for sending chat requests to the configured LLM endpoint."""

    base_url: str = DEFAULT_OLLAMA_URL
    timeout_seconds: float = DEFAULT_TIMEOUT_SECONDS
    max_retries: int = DEFAULT_MAX_RETRIES
    retry_delay_seconds: float = DEFAULT_RETRY_DELAY_SECONDS

    def generate(
        self,
        prompt: str,
        model: Optional[str] = None,
        temperature: float = 0.1,
        purpose: str = "default",
        timeout: Optional[float] = None,
        max_retries: Optional[int] = None,
        system: Optional[str] = None,
    ) -> str:
        resolved_model = resolve_model(purpose=purpose, override=model)
        effective_timeout = timeout if timeout is not None else self.timeout_seconds
        attempts = 1 + (self.max_retries if max_retries is None else max(0, max_retries))

        messages = []
        if system:
            messages.append({"role": "system", "content": system})
        messages.append({"role": "user", "content": prompt})

        payload = {
            "model": resolved_model,
            "messages": messages,
            "options": {"temperature": temperature},
            "stream": False,
        }

        last_error: Optional[Exception] = None
        t_start = time.monotonic()

        for attempt in range(1, attempts + 1):
            try:
                response = requests.post(self.base_url, json=payload, timeout=effective_timeout)
            except requests.Timeout as exc:
                last_error = exc
                if attempt < attempts:
                    time.sleep(self.retry_delay_seconds)
                    continue
                duration_ms = int((time.monotonic() - t_start) * 1000)
                _write_audit_log(purpose, resolved_model, prompt, duration_ms, error=str(exc))
                raise RuntimeError(
                    f"Timed out contacting Ollama at {self.base_url} after {effective_timeout} seconds "
                    f"for model '{resolved_model}' on {attempt} attempt(s)."
                ) from exc
            except requests.RequestException as exc:
                last_error = exc
                if attempt < attempts:
                    time.sleep(self.retry_delay_seconds)
                    continue
                duration_ms = int((time.monotonic() - t_start) * 1000)
                _write_audit_log(purpose, resolved_model, prompt, duration_ms, error=str(exc))
                raise RuntimeError(
                    f"Failed to connect to Ollama at {self.base_url} for model '{resolved_model}': "
                    f"{type(exc).__name__}: {exc}"
                ) from exc

            if not response.ok:
                if response.status_code >= 500 and attempt < attempts:
                    time.sleep(self.retry_delay_seconds)
                    continue
                duration_ms = int((time.monotonic() - t_start) * 1000)
                err_msg = f"HTTP {response.status_code}: {_response_text(response)}"
                _write_audit_log(purpose, resolved_model, prompt, duration_ms, error=err_msg)
                raise RuntimeError(
                    f"Ollama error {response.status_code} for model '{resolved_model}': "
                    f"{_response_text(response)}"
                )

            try:
                data = response.json()
            except ValueError as exc:
                duration_ms = int((time.monotonic() - t_start) * 1000)
                _write_audit_log(purpose, resolved_model, prompt, duration_ms, error=str(exc))
                raise ValueError(
                    f"Failed to parse Ollama HTTP response as JSON for model '{resolved_model}': "
                    f"{_response_text(response)}"
                ) from exc

            message = data.get("message", {})
            content = message.get("content", "")

            if not content:
                duration_ms = int((time.monotonic() - t_start) * 1000)
                _write_audit_log(purpose, resolved_model, prompt, duration_ms, error="empty content")
                raise ValueError(f"Ollama returned empty message content for model '{resolved_model}': {data}")

            duration_ms = int((time.monotonic() - t_start) * 1000)
            _write_audit_log(purpose, resolved_model, prompt, duration_ms)
            return content

        duration_ms = int((time.monotonic() - t_start) * 1000)
        _write_audit_log(purpose, resolved_model, prompt, duration_ms, error=str(last_error))
        raise RuntimeError(
            f"LLM request failed for model '{resolved_model}' after {attempts} attempt(s)."
        ) from last_error


_DEFAULT_CLIENT = LLMClient()


def ollama_chat(
    prompt: str,
    model: Optional[str] = None,
    temperature: float = 0.1,
    purpose: str = "default",
    timeout: Optional[float] = None,
    max_retries: Optional[int] = None,
    system: Optional[str] = None,
) -> str:
    return _DEFAULT_CLIENT.generate(
        prompt=prompt, model=model, temperature=temperature,
        purpose=purpose, timeout=timeout, max_retries=max_retries, system=system,
    )


def llm_json(
    prompt: str,
    model: Optional[str] = None,
    temperature: float = 0.1,
    purpose: str = "default",
    timeout: Optional[float] = None,
    max_retries: Optional[int] = None,
    system: Optional[str] = None,
) -> Dict[str, Any]:
    output = ollama_chat(
        prompt=prompt, model=model, temperature=temperature,
        purpose=purpose, timeout=timeout, max_retries=max_retries, system=system,
    )
    return parse_json_response(output)
