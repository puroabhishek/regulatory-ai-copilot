"""Check that required markdown sections are present in generated policy output."""

import re
from typing import Dict, List


def check_sections(output: str, required_sections: List[str]) -> Dict[str, bool]:
    """Return a dict of section_name → found for each required section."""
    results = {}
    for section in required_sections:
        pattern = re.compile(
            r"^#{1,3}\s+" + re.escape(section),
            re.IGNORECASE | re.MULTILINE,
        )
        results[section] = bool(pattern.search(output))
    return results


def score_sections(output: str, required_sections: List[str]) -> Dict[str, object]:
    """Return section presence map plus a summary ratio."""
    presence = check_sections(output, required_sections)
    found = sum(1 for v in presence.values() if v)
    total = len(required_sections)
    return {
        "sections": presence,
        "found": found,
        "total": total,
        "ratio": round(found / total, 2) if total else 1.0,
        "passed": found == total,
    }
