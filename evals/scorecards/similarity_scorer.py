"""Measure stylistic similarity between generated output and a reference policy."""

import difflib
from pathlib import Path
from typing import Optional


def token_overlap_ratio(text_a: str, text_b: str) -> float:
    """Compute difflib SequenceMatcher ratio between two texts.

    Useful as a rough proxy for stylistic and structural similarity.
    Scores near 1.0 mean near-identical; scores near 0.0 mean very different.
    For policy generation, a ratio > 0.25 against the reference is a reasonable
    baseline — policies won't be identical, but structure and key phrases should overlap.
    """
    return difflib.SequenceMatcher(None, text_a[:4000], text_b[:4000]).ratio()


def score_similarity(
    generated: str,
    reference_file: Optional[str] = None,
    reference_text: Optional[str] = None,
) -> dict:
    """Score generated output against a reference policy.

    Pass either reference_file (path) or reference_text directly.
    """
    if reference_text is None:
        if reference_file is None:
            return {"ratio": None, "note": "no reference provided"}
        ref_path = Path(reference_file)
        if not ref_path.exists():
            return {"ratio": None, "note": f"reference file not found: {reference_file}"}
        reference_text = ref_path.read_text(encoding="utf-8")

    ratio = token_overlap_ratio(generated, reference_text)
    return {
        "ratio": round(ratio, 3),
        "passed": ratio >= 0.15,
        "note": (
            "good stylistic match" if ratio >= 0.25
            else "low similarity — check if tone and structure match reference"
        ),
    }
