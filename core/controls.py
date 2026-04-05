"""Compatibility wrapper for legacy control-extraction imports.

The reusable extraction rules now live in ``domain.regulations`` and
``domain.controls``. Export helpers live in ``services.exports``. This module
stays in place temporarily so current callers do not need to move all at once.
"""

from domain.controls.registry import extract_controls_from_pages
from core.classifier import (
    delete_classification_override,
    list_classification_overrides,
    save_classification_override,
)
from services.exports.control_exports import save_controls_csv, save_controls_json


__all__ = [
    "extract_controls_from_pages",
    "save_controls_json",
    "save_controls_csv",
    "save_classification_override",
    "list_classification_overrides",
    "delete_classification_override",
]
