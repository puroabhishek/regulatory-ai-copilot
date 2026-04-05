"""Rule-based classification helpers for regulatory obligations.

The rules are now loaded from ``configs/control_taxonomy.json`` so topic and
modality tuning can happen without editing Python code.
"""

from typing import Dict, Optional

from configs.control_taxonomy import get_modality_priority, get_topic_default, get_topic_rules


def detect_modality(sentence: str) -> Optional[str]:
    """Detect the strongest applicable obligation modality in a sentence."""
    low = f" {str(sentence or '').lower()} "
    for modal in get_modality_priority():
        if f" {modal} " in low or low.startswith(modal + " "):
            return modal.upper()
    return None


def detect_topic(sentence: str) -> str:
    """Map a sentence to a coarse regulatory topic using keyword rules."""
    low = str(sentence or "").lower()
    for rule in get_topic_rules():
        label = str(rule.get("label", "")).strip()
        for needle in rule.get("keywords", []):
            if needle and needle in low:
                return label
    return get_topic_default()


def classify_regulatory_text(sentence: str) -> Dict[str, Optional[str]]:
    """Return the rule-based modality and topic classification for a sentence."""
    return {
        "modality": detect_modality(sentence),
        "topic": detect_topic(sentence),
    }
