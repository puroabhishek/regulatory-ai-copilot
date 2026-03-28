"""Export helpers for canonical control records.

These helpers keep JSON and CSV serialization out of the domain layer while
preserving the existing on-disk formats used by the current application.
"""

import csv
import json
from pathlib import Path
from typing import Any, Dict, List


CONTROL_EXPORT_FIELDS = [
    "control_id",
    "type",
    "topic",
    "clause",
    "statement",
    "doc_title",
    "page",
    "doc_id",
    "category",
    "control_type",
    "severity",
    "policy_tags",
    "implementation_hint",
]


def save_controls_json(controls: List[Dict[str, Any]], out_path: str) -> str:
    """Serialize canonical controls to JSON."""
    Path(out_path).parent.mkdir(parents=True, exist_ok=True)
    with open(out_path, "w", encoding="utf-8") as handle:
        json.dump(controls, handle, ensure_ascii=False, indent=2)
    return out_path


def save_controls_csv(controls: List[Dict[str, Any]], out_path: str) -> str:
    """Serialize canonical controls to CSV."""
    Path(out_path).parent.mkdir(parents=True, exist_ok=True)

    with open(out_path, "w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=CONTROL_EXPORT_FIELDS)
        writer.writeheader()
        for control in controls:
            row = dict(control)
            if isinstance(row.get("policy_tags"), list):
                row["policy_tags"] = "; ".join(row["policy_tags"])
            writer.writerow({key: row.get(key) for key in CONTROL_EXPORT_FIELDS})

    return out_path
