"""LLM-as-judge scorer for policy generation quality.

Uses a separate judge prompt and ideally a different (larger) model than the
generation model, so the model is not judging its own output.

Set EVAL_JUDGE_MODEL in .env to configure the judge model.
Defaults to the same as POLICY_GENERATION_MODEL if not set.
"""

import os
from pathlib import Path
from typing import Dict, Optional

from prompts.loader import render_prompt
from services.llm.client import llm_json

_REFERENCE_EXCERPT_CHARS = 1200


def judge_policy(
    generated_policy: str,
    reference_policy_file: Optional[str] = None,
    reference_policy_text: Optional[str] = None,
    model: Optional[str] = None,
) -> Dict:
    """Score a generated policy 1–10 using an LLM judge.

    Returns dict with score, rationale, strongest_section, weakest_section,
    top_improvement.
    """
    ref_text = ""
    if reference_policy_text:
        ref_text = reference_policy_text[:_REFERENCE_EXCERPT_CHARS]
    elif reference_policy_file:
        ref_path = Path(reference_policy_file)
        if ref_path.exists():
            ref_text = ref_path.read_text(encoding="utf-8")[:_REFERENCE_EXCERPT_CHARS]

    prompt = render_prompt(
        "tasks.eval_judge_policy",
        reference_policy_excerpt=ref_text or "(no reference provided)",
        generated_policy=generated_policy[:6000],
    )

    judge_model = model or os.getenv("EVAL_JUDGE_MODEL", "").strip() or None
    return llm_json(prompt=prompt, model=judge_model, temperature=0.1, purpose="default")
