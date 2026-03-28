"""PDF parsing helpers for the ingestion layer.

The functions in this module are intentionally focused on extraction only.
They do not know about UI concerns or workflow orchestration; they only convert
PDF bytes into page-level text and a normalized document payload.
"""

from io import BytesIO
from typing import Any, Dict, List

from services.ingestion.text_reader import clean_text


def extract_pdf_pages(file_bytes: bytes) -> List[Dict[str, Any]]:
    """Extract cleaned text for each page in a PDF."""
    try:
        from pypdf import PdfReader
    except Exception:
        try:
            from PyPDF2 import PdfReader
        except Exception as exc:
            raise RuntimeError("PDF support requires pypdf or PyPDF2. Install one of them first.") from exc

    reader = PdfReader(BytesIO(file_bytes))
    pages: List[Dict[str, Any]] = []

    for i, page in enumerate(reader.pages, start=1):
        page_text = page.extract_text() or ""
        pages.append({"page": i, "text": clean_text(page_text)})

    return pages


def read_pdf(file_bytes: bytes) -> Dict[str, Any]:
    """Return normalized text extraction results for a PDF file."""
    pages = extract_pdf_pages(file_bytes)
    page_texts = [p.get("text", "") for p in pages if p.get("text")]
    extracted_text = "\n\n".join(page_texts).strip()

    warnings: List[str] = []
    blank_pages = sum(1 for p in pages if not p.get("text"))
    if blank_pages:
        warnings.append(
            f"{blank_pages} page(s) did not produce extractable text. OCR is not supported yet."
        )
    if not extracted_text:
        warnings.append("No text could be extracted from the PDF. OCR is not supported yet.")

    return {
        "extracted_text": extracted_text,
        "cleaned_text": extracted_text,
        "structured_rows": [],
        "warnings": warnings,
        "pages": pages,
    }
