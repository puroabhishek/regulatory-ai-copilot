"""Central file-loader entrypoints for the ingestion layer.

This module provides adapter-style wrappers around the format-specific readers
under ``services.ingestion``. Callers should use these helpers instead of
parsing uploaded files or local files directly.
"""

from pathlib import Path
from typing import Any, Dict, Optional, Union

from services.ingestion.csv_reader import read_csv
from services.ingestion.docx_reader import read_docx
from services.ingestion.pdf_reader import read_pdf
from services.ingestion.text_reader import read_text
from services.ingestion.xlsx_reader import read_xlsx


NormalizedIngestionResult = Dict[str, Any]

SUPPORTED_FILE_TYPES = {"txt", "md", "pdf", "docx", "csv", "xlsx"}


def normalize_file_type(source_name: str, file_type: Optional[str] = None) -> str:
    """Normalize a provided or inferred file type to a lowercase extension name."""
    if file_type and str(file_type).strip():
        normalized = str(file_type).strip().lower().lstrip(".")
    else:
        normalized = Path(source_name).suffix.lower().lstrip(".")

    if normalized == "doc":
        raise RuntimeError("Legacy .doc is not supported directly. Please convert it to .docx or PDF.")

    if normalized not in SUPPORTED_FILE_TYPES:
        raise RuntimeError(
            f"Unsupported file type: .{normalized}" if normalized else "Unable to determine file type."
        )

    return normalized


def load_file_bytes(path: Union[str, Path]) -> bytes:
    """Load raw bytes from a local filesystem path."""
    return Path(path).read_bytes()


def _uploaded_file_bytes(uploaded_file: Any) -> bytes:
    if hasattr(uploaded_file, "getvalue"):
        return uploaded_file.getvalue()
    if hasattr(uploaded_file, "read"):
        return uploaded_file.read()
    raise TypeError("Uploaded file object must provide getvalue() or read().")


def _base_result(source_name: str, file_type: str) -> NormalizedIngestionResult:
    return {
        "source_name": source_name,
        "file_type": file_type,
        "extracted_text": "",
        "cleaned_text": "",
        "structured_rows": [],
        "warnings": [],
        "pages": [],
    }


def parse_file_bytes(
    file_bytes: bytes,
    source_name: str,
    file_type: Optional[str] = None,
) -> NormalizedIngestionResult:
    """Parse raw file bytes into a normalized ingestion result."""
    normalized_type = normalize_file_type(source_name=source_name, file_type=file_type)
    result = _base_result(source_name=source_name, file_type=normalized_type)

    if normalized_type in {"txt", "md"}:
        cleaned = read_text(file_bytes)
        result.update(
            {
                "extracted_text": cleaned,
                "cleaned_text": cleaned,
            }
        )
        if not cleaned:
            result["warnings"].append("No text could be extracted from the file.")
        return result

    if normalized_type == "pdf":
        result.update(read_pdf(file_bytes))
        return result

    if normalized_type == "docx":
        result.update(read_docx(file_bytes))
        return result

    if normalized_type == "csv":
        result.update(read_csv(file_bytes))
        return result

    if normalized_type == "xlsx":
        result.update(read_xlsx(file_bytes))
        return result

    raise RuntimeError(f"Unsupported file type: .{normalized_type}")


def parse_file_path(path: Union[str, Path], file_type: Optional[str] = None) -> NormalizedIngestionResult:
    """Load and parse a local file path into the normalized ingestion structure."""
    path_obj = Path(path)
    return parse_file_bytes(
        file_bytes=load_file_bytes(path_obj),
        source_name=path_obj.name,
        file_type=file_type,
    )


def parse_uploaded_file(uploaded_file: Any, file_type: Optional[str] = None) -> NormalizedIngestionResult:
    """Parse a Streamlit-style uploaded file object into the normalized structure."""
    source_name = getattr(uploaded_file, "name", "uploaded_file")
    return parse_file_bytes(
        file_bytes=_uploaded_file_bytes(uploaded_file),
        source_name=source_name,
        file_type=file_type,
    )
