"""Workflow helpers for regulation ingestion, storage, indexing, and search.

This module keeps multi-step document flows out of Streamlit pages while
preserving the current file-based behavior.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List

from core.chunk import load_pages_jsonl, pages_to_chunks
from core.index import (
    get_active_index_backend,
    get_index_backend_notice,
    index_chunks,
    query_index,
)
from core.ingest import save_pages
from core.postprocess import extract_requirements
from services.ingestion.file_loader import parse_uploaded_file


PROCESSED_DIR = Path("data/processed")


def list_processed_page_files(processed_dir: str = str(PROCESSED_DIR)) -> List[str]:
    """Return saved processed regulation files available for indexing and extraction."""

    directory = Path(processed_dir)
    if not directory.exists():
        return []
    return sorted(path.name for path in directory.glob("*_pages.jsonl"))


def get_index_status() -> Dict[str, str]:
    """Return user-facing information about the currently configured index backend."""

    return {
        "backend": get_active_index_backend(),
        "notice": get_index_backend_notice(),
    }


def prepare_uploaded_regulation_pages(
    uploaded_file: Any,
    file_type: str = "pdf",
) -> Dict[str, Any]:
    """Parse an uploaded regulation file without persisting it yet."""

    parsed_upload = parse_uploaded_file(uploaded_file, file_type=file_type)
    pages = parsed_upload.get("pages", [])
    doc_title = parsed_upload.get("source_name", "uploaded_document")
    doc_id = Path(doc_title).stem.lower().replace(" ", "_")
    total_chars = sum(len(page.get("text", "") or "") for page in pages)

    return {
        "doc_id": doc_id,
        "doc_title": doc_title,
        "pages": pages,
        "warnings": parsed_upload.get("warnings", []),
        "total_chars": total_chars,
        "suggested_output_path": str(Path(PROCESSED_DIR) / f"{doc_id}_pages.jsonl"),
    }


def persist_extracted_pages(
    pages: List[Dict[str, Any]],
    doc_id: str,
    doc_title: str,
    processed_dir: str = str(PROCESSED_DIR),
) -> str:
    """Persist extracted page records after the user confirms the save action."""

    out_path = Path(processed_dir) / f"{doc_id}_pages.jsonl"
    return save_pages(pages=pages, out_path=str(out_path), doc_id=doc_id, doc_title=doc_title)


def build_index_for_processed_file(
    selected_file: str,
    chunk_tokens: int,
    overlap_tokens: int,
    processed_dir: str = str(PROCESSED_DIR),
) -> Dict[str, Any]:
    """Load a processed regulation file, chunk it, and update the index."""

    pages = load_pages_jsonl(str(Path(processed_dir) / selected_file))
    chunks = pages_to_chunks(
        pages=pages,
        chunk_tokens=chunk_tokens,
        overlap_tokens=overlap_tokens,
    )
    added, skipped = index_chunks(chunks)

    return {
        "selected_file": selected_file,
        "chunk_count": len(chunks),
        "added": added,
        "skipped": skipped,
    }


def search_processed_index(query: str, top_k: int = 8) -> Dict[str, Any]:
    """Search the current index and return both raw results and checklist output."""

    result = query_index(query.strip(), top_k=top_k)

    ids = result.get("ids", [[]])
    docs = result.get("documents", [[]])
    metas = result.get("metadatas", [[]])
    distances = result.get("distances", [[]])

    if not ids or not ids[0]:
        return {
            "result": result,
            "retrieved": [],
            "requirements": [],
        }

    retrieved = []
    for index in range(len(ids[0])):
        retrieved.append(
            {
                "chunk_id": ids[0][index],
                "text": docs[0][index],
                "meta": metas[0][index],
                "distance": distances[0][index],
            }
        )

    return {
        "result": result,
        "retrieved": retrieved,
        "requirements": extract_requirements(retrieved, max_items=20),
    }
