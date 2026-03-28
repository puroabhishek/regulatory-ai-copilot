"""LLM request client utilities.

This module owns outbound chat requests to the configured model endpoint.
Its job is to:
- resolve the target model for a workflow purpose
- send the request with sensible timeout defaults
- retry transient failures a small number of times
- return normalized text content for downstream parsing
"""

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
    ) -> str:
        """Send a chat request and return the model's text content."""
        resolved_model = resolve_model(purpose=purpose, override=model)
        effective_timeout = timeout if timeout is not None else self.timeout_seconds
        attempts = 1 + (self.max_retries if max_retries is None else max(0, max_retries))

        payload = {
            "model": resolved_model,
            "messages": [{"role": "user", "content": prompt}],
            "options": {"temperature": temperature},
            "stream": False,
        }

        last_error: Optional[Exception] = None

        for attempt in range(1, attempts + 1):
            try:
                response = requests.post(self.base_url, json=payload, timeout=effective_timeout)
            except requests.Timeout as exc:
                last_error = exc
                if attempt < attempts:
                    time.sleep(self.retry_delay_seconds)
                    continue
                raise RuntimeError(
                    f"Timed out contacting Ollama at {self.base_url} after {effective_timeout} seconds "
                    f"for model '{resolved_model}' on {attempt} attempt(s)."
                ) from exc
            except requests.RequestException as exc:
                last_error = exc
                if attempt < attempts:
                    time.sleep(self.retry_delay_seconds)
                    continue
                raise RuntimeError(
                    f"Failed to connect to Ollama at {self.base_url} for model '{resolved_model}': "
                    f"{type(exc).__name__}: {exc}"
                ) from exc

            if not response.ok:
                if response.status_code >= 500 and attempt < attempts:
                    time.sleep(self.retry_delay_seconds)
                    continue

                raise RuntimeError(
                    f"Ollama error {response.status_code} for model '{resolved_model}': "
                    f"{_response_text(response)}"
                )

            try:
                data = response.json()
            except ValueError as exc:
                raise ValueError(
                    f"Failed to parse Ollama HTTP response as JSON for model '{resolved_model}': "
                    f"{_response_text(response)}"
                ) from exc

            message = data.get("message", {})
            content = message.get("content", "")

            if not content:
                raise ValueError(f"Ollama returned empty message content for model '{resolved_model}': {data}")

            return content

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
) -> str:
    """Compatibility helper that returns raw text from the configured LLM."""
    return _DEFAULT_CLIENT.generate(
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
    """Request a response and parse the returned content as structured JSON."""
    output = ollama_chat(
        prompt=prompt,
        model=model,
        temperature=temperature,
        purpose=purpose,
        timeout=timeout,
        max_retries=max_retries,
    )
    return parse_json_response(output)
