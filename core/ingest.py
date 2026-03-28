import json
from pathlib import Path
from typing import List, Dict, Any

from services.ingestion.file_loader import parse_file_path
from services.ingestion.text_reader import clean_text as normalize_text


def clean_text(text: str) -> str:
    """
    What it does:
    - Normalizes whitespace and removes junk spacing.
    Why:
    - Cleaner chunks -> better retrieval later.
    """
    return normalize_text(text)


def pdf_to_pages(pdf_path: str) -> List[Dict[str, Any]]:
    """
    What it does:
    - Reads a PDF and returns a list of pages with page number + text.
    Why:
    - We need page-level provenance for citations later.
    """
    parsed = parse_file_path(pdf_path, file_type="pdf")
    return parsed.get("pages", [])


def save_pages(pages: List[Dict[str, Any]], out_path: str, doc_id: str, doc_title: str) -> str:
    """
    What it does:
    - Saves extracted pages as JSONL (one JSON per line).
    Why:
    - JSONL is easy to stream, debug, and later chunk/index.
    """
    Path(out_path).parent.mkdir(parents=True, exist_ok=True)

    with open(out_path, "w", encoding="utf-8") as f:
        for p in pages:
            record = {
                "doc_id": doc_id,
                "doc_title": doc_title,
                "page": p["page"],
                "text": p["text"],
            }
            f.write(json.dumps(record, ensure_ascii=False) + "\n")

    return out_path
