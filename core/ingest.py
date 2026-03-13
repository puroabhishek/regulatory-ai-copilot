import os
import re
import json
from pathlib import Path
from typing import List, Dict, Any

from pypdf import PdfReader


def clean_text(text: str) -> str:
    """
    What it does:
    - Normalizes whitespace and removes junk spacing.
    Why:
    - Cleaner chunks -> better retrieval later.
    """
    if not text:
        return ""
    text = text.replace("\x00", " ")
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def pdf_to_pages(pdf_path: str) -> List[Dict[str, Any]]:
    """
    What it does:
    - Reads a PDF and returns a list of pages with page number + text.
    Why:
    - We need page-level provenance for citations later.
    """
    reader = PdfReader(pdf_path)
    pages = []
    for i, page in enumerate(reader.pages, start=1):
        text = page.extract_text() or ""
        pages.append({"page": i, "text": clean_text(text)})
    return pages


def save_pages(pages: List[Dict[str, Any]], out_path: str, doc_id: str, doc_title: str) -> str:
    """
    What it does:
    - Saves extracted pages as JSONL (one JSON per line).
    Why:
    - JSONL is easy to stream, debug, and later chunk/index.
    """
    Path(os.path.dirname(out_path)).mkdir(parents=True, exist_ok=True)

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