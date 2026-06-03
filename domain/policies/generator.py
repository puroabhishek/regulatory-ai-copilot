"""Markdown policy drafting from a structured blueprint.

This module takes a structured policy blueprint and turns it into a final policy
draft in markdown. It owns prompt construction and model invocation, but does
not perform any file I/O or UI rendering.
"""

import json
from typing import Any, Optional

from prompts.loader import render_prompt, system_prompt
from services.llm.client import ollama_chat
from schemas.common import ensure_schema
from schemas.policy import Policy

_REFERENCE_EXCERPT_CHARS = 1500


def _build_blueprint_context(policy_blueprint: Any) -> str:
    blueprint_model = ensure_schema(policy_blueprint, Policy)
    return json.dumps(blueprint_model.to_dict(), ensure_ascii=False, indent=2)


def build_policy_markdown_prompt(policy_blueprint: Any) -> str:
    """Build the drafting prompt for the final markdown generation step."""
    blueprint_model = ensure_schema(policy_blueprint, Policy)
    style_reference = str(blueprint_model.style_reference_excerpt or "").strip()
    drafting_instructions = str(blueprint_model.drafting_instructions or "").strip()

    reference_policy_block = ""
    if style_reference:
        excerpt = style_reference[:_REFERENCE_EXCERPT_CHARS]
        reference_policy_block = (
            "REFERENCE POLICY EXAMPLE (match this style, tone, and level of specificity):\n"
            "---\n"
            f"{excerpt}\n"
            "---"
        )

    drafting_instructions_block = ""
    if drafting_instructions:
        drafting_instructions_block = f"DRAFTING INSTRUCTIONS:\n{drafting_instructions}"

    return render_prompt(
        "tasks.policy_generation",
        blueprint_json=_build_blueprint_context(policy_blueprint),
        reference_policy_block=reference_policy_block,
        drafting_instructions_block=drafting_instructions_block,
    )


def generate_policy_markdown_from_blueprint(
    policy_blueprint: Any,
    model: Optional[str] = None,
) -> str:
    """Generate final markdown from a structured policy blueprint."""
    prompt = build_policy_markdown_prompt(policy_blueprint)
    return ollama_chat(
        prompt=prompt,
        system=system_prompt("policy_drafter"),
        model=model,
        temperature=0.1,
        purpose="policy_generation",
    )
