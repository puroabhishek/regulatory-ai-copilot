"""Normalization helpers for regulation text.

This module keeps low-level text cleanup and sentence preparation separate from
classification and control-building logic so the same normalization rules can be
reused across regulation ingestion flows.
"""

import re
from typing import List, Optional


CLAUSE_RE = re.compile(r"\b(?P<clause>\d+(?:\.\d+){1,3})\.\s+")
SENTENCE_SPLIT_RE = re.compile(r"(?<=[\.\n])\s+")


def normalize_whitespace(text: str) -> str:
    """Normalize whitespace and common non-breaking spaces."""
    normalized = str(text or "").replace("\u00a0", " ")
    normalized = re.sub(r"\s+", " ", normalized).strip()
    return normalized


def is_table_like(text: str) -> bool:
    """Detect obvious table-like or symbol-heavy fragments that should be skipped."""
    if "✓" in text or "" in text:
        return True
    if len(re.findall(r"\s{4,}", text)) > 0:
        return True
    return False


def split_regulation_text(text: str) -> List[str]:
    """Split normalized regulation text into candidate obligation sentences."""
    normalized = normalize_whitespace(text)
    parts = SENTENCE_SPLIT_RE.split(normalized)
    return [normalize_whitespace(part) for part in parts if normalize_whitespace(part)]


def extract_clause_number(text: str) -> Optional[str]:
    """Extract a clause number when the text starts with a numbered clause."""
    match = CLAUSE_RE.search(text)
    if not match:
        return None
    return match.group("clause")


def strip_clause_prefix(text: str) -> str:
    """Remove a leading clause prefix from a candidate obligation."""
    return re.sub(r"^\s*\d+(?:\.\d+){1,3}\.\s*", "", text).strip()


def make_dedupe_key(text: str) -> str:
    """Build a stable dedupe key for a normalized obligation statement."""
    return re.sub(r"\s+", " ", str(text or "").lower()).strip()
