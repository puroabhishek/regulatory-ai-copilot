from typing import Dict, Any

from core.llm import llm_json


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
    data = llm_json(build_classification_prompt(control_text), model=model)

    return {
        "category": str(data.get("category", "")).strip(),
        "control_type": str(data.get("control_type", "")).strip(),
        "severity": str(data.get("severity", "")).strip(),
        "policy_tags": data.get("policy_tags", []) if isinstance(data.get("policy_tags", []), list) else [],
        "implementation_hint": str(data.get("implementation_hint", "")).strip(),
    }