"""Canonical control builders for regulation-derived obligations.

This module converts normalized regulation text into canonical control records.
It keeps control extraction and canonicalization in the domain layer while
delegating file export responsibilities elsewhere.
"""

from typing import Any, Dict, List, Optional

from core.classifier import classify_control
from domain.regulations.classifier import classify_regulatory_text
from domain.regulations.normalizer import (
    extract_clause_number,
    is_table_like,
    make_dedupe_key,
    normalize_whitespace,
    split_regulation_text,
    strip_clause_prefix,
)
from schemas.control import Control


EMPTY_CLASSIFICATION = {
    "category": "",
    "control_type": "",
    "severity": "",
    "policy_tags": [],
    "implementation_hint": "",
}


def make_control_id(prefix: str, clause: Optional[str], page: int, idx: int) -> str:
    """Build a canonical control identifier from clause or page context."""
    if clause:
        return f"{prefix}-{clause}"
    return f"{prefix}-P{page}-I{idx}"


def build_control_record(
    statement: str,
    doc_id: str,
    doc_title: str,
    page_num: int,
    item_index: int,
    prefix: str,
    clause: Optional[str],
    modality: str,
    topic: str,
    model: str,
) -> Control:
    """Convert a classified obligation into the canonical control structure."""
    try:
        extra = classify_control(statement, model=model)
    except Exception:
        extra = dict(EMPTY_CLASSIFICATION)

    return Control(
        control_id=make_control_id(prefix, clause, page_num, item_index),
        doc_id=doc_id,
        doc_title=doc_title,
        page=page_num,
        clause=clause or "",
        type=modality,
        topic=topic,
        statement=statement,
        category=extra["category"],
        control_type=extra["control_type"],
        severity=extra["severity"],
        policy_tags=extra["policy_tags"],
        implementation_hint=extra["implementation_hint"],
    )


def extract_controls_from_pages(
    pages: List[Dict[str, Any]],
    doc_id: str,
    doc_title: str,
    prefix: str = "QCB-CCR",
    min_len: int = 50,
    max_len: int = 500,
    model: str = "qwen2.5:1.5b",
) -> List[Dict[str, Any]]:
    """Extract canonical controls from page-level regulation text."""
    controls: List[Dict[str, Any]] = []
    seen = set()

    for page in pages:
        page_num = int(page.get("page", 0))
        raw_text = normalize_whitespace(page.get("text", "") or "")

        for item_index, candidate in enumerate(split_regulation_text(raw_text)):
            if len(candidate) < min_len or len(candidate) > max_len:
                continue
            if is_table_like(candidate):
                continue

            classification = classify_regulatory_text(candidate)
            modality = classification.get("modality")
            if not modality:
                continue

            clause = extract_clause_number(candidate)
            statement = strip_clause_prefix(candidate)
            dedupe_key = make_dedupe_key(statement)

            if dedupe_key in seen:
                continue
            seen.add(dedupe_key)

            controls.append(
                build_control_record(
                    statement=statement,
                    doc_id=doc_id,
                    doc_title=doc_title,
                    page_num=page_num,
                    item_index=item_index,
                    prefix=prefix,
                    clause=clause,
                    modality=modality,
                    topic=classification.get("topic", "General") or "General",
                    model=model,
                ).to_dict()
            )

    return controls
