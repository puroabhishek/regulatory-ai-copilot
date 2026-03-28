"""Markdown policy drafting from a structured blueprint.

This module takes a structured policy blueprint and turns it into a final policy
draft in markdown. It owns prompt construction and model invocation, but does
not perform any file I/O or UI rendering.
"""

import json
from typing import Any, Optional

from services.llm.client import ollama_chat
from schemas.common import ensure_schema
from schemas.policy import Policy


def _build_blueprint_context(policy_blueprint: Any) -> str:
    blueprint_model = ensure_schema(policy_blueprint, Policy)
    return json.dumps(blueprint_model.to_dict(), ensure_ascii=False, indent=2)


def build_policy_markdown_prompt(policy_blueprint: Any) -> str:
    """Build the drafting prompt for the final markdown generation step."""
    blueprint_model = ensure_schema(policy_blueprint, Policy)
    style_reference = str(blueprint_model.style_reference_excerpt or "").strip()
    drafting_instructions = str(blueprint_model.drafting_instructions or "").strip()

    return f"""
You are drafting a bespoke regulatory policy for a business.

Return ONLY markdown.
Do not explain your reasoning.

STRUCTURED POLICY BLUEPRINT:
{_build_blueprint_context(policy_blueprint)}

OPTIONAL SAMPLE POLICY STYLE / REFERENCE:
{style_reference}

OPTIONAL DRAFTING INSTRUCTIONS:
{drafting_instructions}

Requirements:
1. Draft a business-specific policy.
2. Use the structured blueprint as the authoritative drafting plan.
3. Reflect the business profile and control-linked policy statements captured in the blueprint.
4. If lending-related context exists, reflect partner/KYC/accountability structure where relevant.
5. Use these sections:
   - Purpose
   - Scope
   - Definitions
   - Roles and Responsibilities
   - Policy Statements
   - Procedures
   - Records
   - Exceptions
   - Review
6. Keep the document practical, formal, and implementation-oriented.
7. Return only markdown.
"""


def generate_policy_markdown_from_blueprint(
    policy_blueprint: Any,
    model: Optional[str] = None,
) -> str:
    """Generate final markdown from a structured policy blueprint."""
    prompt = build_policy_markdown_prompt(policy_blueprint)
    return ollama_chat(
        prompt=prompt,
        model=model,
        temperature=0.1,
        purpose="policy_generation",
    )
