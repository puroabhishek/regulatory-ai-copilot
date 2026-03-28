"""DOCX parsing helpers for the ingestion layer."""

from io import BytesIO
from typing import Any, Dict, List

from services.ingestion.text_reader import clean_text


def read_docx(file_bytes: bytes) -> Dict[str, Any]:
    """Extract cleaned text from a DOCX file."""
    try:
        from docx import Document
    except Exception as exc:
        raise RuntimeError("Word support requires python-docx. Install it first.") from exc

    document = Document(BytesIO(file_bytes))
    paragraphs = [p.text for p in document.paragraphs if p.text and p.text.strip()]
    extracted_text = "\n\n".join(paragraphs).strip()
    cleaned = clean_text(extracted_text)

    warnings: List[str] = []
    if not cleaned:
        warnings.append("No text could be extracted from the DOCX file.")

    return {
        "extracted_text": extracted_text,
        "cleaned_text": cleaned,
        "structured_rows": [],
        "warnings": warnings,
        "pages": [],
    }
