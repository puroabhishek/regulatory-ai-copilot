"""CSV parsing helpers for the ingestion layer."""

import csv
from io import StringIO
from typing import Any, Dict, List

from services.ingestion.text_reader import clean_text


def _rows_to_text(rows: List[Dict[str, Any]]) -> str:
    lines = []
    for row in rows:
        parts = [f"{key}: {value}" for key, value in row.items() if str(value).strip()]
        if parts:
            lines.append(" | ".join(parts))
    return "\n".join(lines).strip()


def read_csv(file_bytes: bytes) -> Dict[str, Any]:
    """Parse CSV bytes into structured rows and flattened text."""
    raw_text = file_bytes.decode("utf-8-sig", errors="ignore")
    buffer = StringIO(raw_text)
    reader = csv.DictReader(buffer)

    rows: List[Dict[str, Any]] = []
    warnings: List[str] = []

    if reader.fieldnames is None:
        warnings.append("CSV file does not contain a header row.")
    else:
        for row in reader:
            rows.append({str(key): str(value or "").strip() for key, value in row.items()})

    extracted_text = _rows_to_text(rows)
    cleaned = clean_text(extracted_text)

    if not rows:
        warnings.append("No structured rows were extracted from the CSV file.")

    return {
        "extracted_text": extracted_text,
        "cleaned_text": cleaned,
        "structured_rows": rows,
        "warnings": warnings,
        "pages": [],
    }
