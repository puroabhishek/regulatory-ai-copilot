"""Utilities for plain-text ingestion and shared text normalization.

This module provides the most basic parsing primitives used by the wider
ingestion layer. Other readers reuse ``clean_text`` so cleanup rules stay
consistent across PDFs, DOCX files, and text-based formats.
"""

import re


def clean_text(text: str) -> str:
    """Normalize whitespace and remove common low-signal formatting artifacts."""
    if not text:
        return ""

    normalized = str(text)
    normalized = normalized.replace("\x00", " ")
    normalized = normalized.replace("\u00a0", " ")
    normalized = normalized.replace("\r\n", "\n").replace("\r", "\n")
    normalized = re.sub(r"[ \t]+", " ", normalized)
    normalized = re.sub(r"\n{3,}", "\n\n", normalized)
    return normalized.strip()


def read_text(file_bytes: bytes, encoding: str = "utf-8") -> str:
    """Decode plain-text bytes and return cleaned text."""
    text = file_bytes.decode(encoding, errors="ignore")
    return clean_text(text)
