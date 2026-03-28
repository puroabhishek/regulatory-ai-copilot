"""Model routing helpers for the LLM service layer.

This module centralizes model selection so callers can ask for a purpose such
as ``gap_analysis`` or ``policy_generation`` without knowing the environment
variable details behind that choice.
"""

import os
from pathlib import Path
from typing import Dict, Optional

from dotenv import load_dotenv


ROOT_DIR = Path(__file__).resolve().parent.parent.parent
load_dotenv(dotenv_path=ROOT_DIR / ".env")


def _purpose_map() -> Dict[str, str]:
    return {
        "control_classifier": os.getenv("CONTROL_CLASSIFIER_MODEL", "").strip(),
        "gap_analysis": os.getenv("GAP_ANALYSIS_MODEL", "").strip(),
        "policy_generation": os.getenv("POLICY_GENERATION_MODEL", "").strip(),
        "default": os.getenv("DEFAULT_LLM_MODEL", "").strip(),
    }


def resolve_model(purpose: str = "default", override: Optional[str] = None) -> str:
    """Resolve the model from an explicit override, purpose-specific value, or default."""
    if override and str(override).strip():
        return str(override).strip()

    purpose_map = _purpose_map()
    default_model = purpose_map.get("default", "")
    resolved = purpose_map.get(purpose, "") or default_model
    resolved = str(resolved or "").strip()

    if not resolved:
        raise ValueError(
            f"No LLM model configured for purpose='{purpose}'. "
            "Set the appropriate value in .env, for example DEFAULT_LLM_MODEL or GAP_ANALYSIS_MODEL."
        )

    return resolved
