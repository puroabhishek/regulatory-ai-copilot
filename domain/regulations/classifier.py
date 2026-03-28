"""Rule-based classification helpers for regulatory obligations.

This module holds the deterministic rules that infer modality and topic from
regulation text. It intentionally preserves the existing rules from the legacy
control extractor so current behavior remains stable during refactoring.
"""

from typing import Dict, Optional


MODAL_PRIORITY = ["must", "shall", "should", "may"]

TOPIC_RULES = [
    ("approval", "Regulatory Approval"),
    ("qcb", "Regulatory Approval"),
    ("register", "Register & Reporting"),
    ("inventory", "Register & Reporting"),
    ("disclose", "Register & Reporting"),
    ("audit", "Assurance & Audit"),
    ("soc", "Assurance & Audit"),
    ("test", "Security Testing"),
    ("penetration", "Security Testing"),
    ("vulnerability", "Security Testing"),
    ("encrypt", "Security Controls"),
    ("authentication", "Security Controls"),
    ("access", "Security Controls"),
    ("confidential", "Data Protection"),
    ("privacy", "Data Protection"),
    ("personal data", "Data Protection"),
    ("pii", "Data Residency"),
    ("within qatar", "Data Residency"),
    ("outsourcing", "Outsourcing & Vendor Risk"),
    ("csp", "Outsourcing & Vendor Risk"),
    ("risk", "Risk Management"),
    ("governance", "Governance"),
    ("board", "Governance"),
    ("strategy", "Governance"),
    ("business continuity", "Resilience & BCP"),
    ("resilien", "Resilience & BCP"),
]


def detect_modality(sentence: str) -> Optional[str]:
    """Detect the strongest applicable obligation modality in a sentence."""
    low = f" {str(sentence or '').lower()} "
    for modal in MODAL_PRIORITY:
        if f" {modal} " in low or low.startswith(modal + " "):
            return modal.upper()
    return None


def detect_topic(sentence: str) -> str:
    """Map a sentence to a coarse regulatory topic using keyword rules."""
    low = str(sentence or "").lower()
    for needle, label in TOPIC_RULES:
        if needle in low:
            return label
    return "General"


def classify_regulatory_text(sentence: str) -> Dict[str, Optional[str]]:
    """Return the rule-based modality and topic classification for a sentence."""
    return {
        "modality": detect_modality(sentence),
        "topic": detect_topic(sentence),
    }
