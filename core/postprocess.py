import re
from typing import List, Dict, Any


KEYWORDS = [
    "must", "should", "shall", "require", "approval",
    "ensure", "establish", "maintain", "define",
    "comply", "risk", "audit", "encrypt", "register"
]


def is_table_like(text: str) -> bool:
    """
    Filters out table rows and symbol-heavy content.
    """
    if "✓" in text or "" in text:
        return True
    if len(re.findall(r"[|]{2,}", text)) > 0:
        return True
    if len(re.findall(r"\s{4,}", text)) > 0:
        return True
    return False


def clean_sentence(text: str) -> str:
    """
    Normalizes spacing and removes weird formatting artifacts.
    """
    text = re.sub(r"\s+", " ", text)
    text = text.replace(" .", ".")
    text = text.strip()
    return text


def extract_requirements(
    results: List[Dict[str, Any]],
    max_items: int = 20,
    max_distance: float = 0.95
) -> List[str]:
    """
    What this improved version does:
    - Filters by semantic distance (removes weak matches)
    - Removes tables and broken formatting
    - Deduplicates cleanly
    - Prefers strong regulatory statements
    """

    items = []
    seen = set()

    for r in results:
        # Skip weak semantic matches
        if r.get("distance", 1.0) > max_distance:
            continue

        text = r.get("text", "")
        parts = re.split(r"(?<=[\.\n])\s+", text)

        for p in parts:
            s = clean_sentence(p)

            # Basic filters
            if len(s) < 60:
                continue
            if is_table_like(s):
                continue

            low = s.lower()

            # Stronger preference: sentence starts with regulatory tone
            strong_start = (
                low.startswith("an entity must")
                or low.startswith("an entity should")
                or low.startswith("the entity must")
                or low.startswith("entity must")
                or low.startswith("must ")
            )

            keyword_match = any(k in low for k in KEYWORDS)

            if strong_start or keyword_match:
                key = re.sub(r"\s+", " ", low)

                if key not in seen:
                    seen.add(key)
                    items.append(s)

            if len(items) >= max_items:
                return items

    return items