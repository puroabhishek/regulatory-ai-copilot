"""Pydantic schemas for saved policy inputs and structured policy content."""

from __future__ import annotations

from typing import Any, Dict, List

from pydantic import Field

from schemas.common import SchemaModel


class Policy(SchemaModel):
    """Policy or policy-blueprint object used by drafting-related workflows."""

    policy_name: str = ""
    title: str = ""
    policy_text: str = ""
    version: str = ""
    objective: str = ""
    scope: List[str] = Field(default_factory=list)
    definitions: List[Dict[str, str]] = Field(default_factory=list)
    responsibilities: List[Dict[str, str]] = Field(default_factory=list)
    policy_statements: List[Dict[str, Any]] = Field(default_factory=list)
    procedures: List[str] = Field(default_factory=list)
    records: List[str] = Field(default_factory=list)
    exceptions: str = ""
    review_cycle: str = ""
    drafting_instructions: str = ""
    selected_control_files: List[str] = Field(default_factory=list)
    selected_profile_file: str = ""
    profile_summary: Dict[str, Any] = Field(default_factory=dict)
    sample_policy_text: str = ""
    style_reference_excerpt: str = ""
    source_context: Dict[str, Any] = Field(default_factory=dict)
