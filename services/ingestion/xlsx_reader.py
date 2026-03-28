"""XLSX parsing helpers for the ingestion layer."""

from io import BytesIO
from typing import Any, Dict, List

from services.ingestion.text_reader import clean_text


def _rows_to_text(rows: List[Dict[str, Any]]) -> str:
    lines = []
    for row in rows:
        parts = [f"{key}: {value}" for key, value in row.items() if str(value).strip()]
        if parts:
            lines.append(" | ".join(parts))
    return "\n".join(lines).strip()


def read_xlsx(file_bytes: bytes) -> Dict[str, Any]:
    """Parse XLSX bytes into structured rows and flattened text."""
    try:
        import pandas as pd
    except Exception as exc:
        raise RuntimeError("XLSX support requires pandas. Install it first.") from exc

    try:
        df = pd.read_excel(BytesIO(file_bytes))
    except Exception as exc:
        raise RuntimeError("Failed to read XLSX file. Ensure a compatible Excel engine is installed.") from exc

    if df.empty:
        rows: List[Dict[str, Any]] = []
    else:
        df = df.fillna("")
        rows = [{str(key): value for key, value in row.items()} for row in df.to_dict(orient="records")]

    extracted_text = _rows_to_text(rows)
    cleaned = clean_text(extracted_text)

    warnings: List[str] = []
    if not rows:
        warnings.append("No structured rows were extracted from the XLSX file.")

    return {
        "extracted_text": extracted_text,
        "cleaned_text": cleaned,
        "structured_rows": rows,
        "warnings": warnings,
        "pages": [],
    }
