import json
import requests
from typing import Dict, Any


def _json_loads_loose(s: str) -> Dict[str, Any]:
    s = s.strip()

    try:
        return json.loads(s)
    except Exception:
        pass

    start = s.find("{")
    end = s.rfind("}")
    if start != -1 and end != -1 and end > start:
        return json.loads(s[start:end + 1])

    raise ValueError("Model did not return valid JSON.")


def ollama_chat(prompt: str, model: str = "qwen2.5:1.5b", temperature: float = 0.1) -> str:
    url = "http://localhost:11434/api/chat"

    payload = {
        "model": model,
        "messages": [{"role": "user", "content": prompt}],
        "options": {"temperature": temperature},
        "stream": False,
    }

    response = requests.post(url, json=payload, timeout=600)
    response.raise_for_status()

    data = response.json()
    return data["message"]["content"]


def llm_json(prompt: str, model: str = "qwen2.5:1.5b", temperature: float = 0.1) -> Dict[str, Any]:
    output = ollama_chat(prompt=prompt, model=model, temperature=temperature)
    return _json_loads_loose(output)