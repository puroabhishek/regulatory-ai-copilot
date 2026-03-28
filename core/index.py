"""Safe indexing helpers for the app.

This module now defaults to a lightweight keyword backend so the app can stay
stable even when native vector-search dependencies are not safe to import in
the current Python runtime. The public function names stay the same so the UI
and other callers do not need to change.
"""

import json
import math
import os
import re
from pathlib import Path
from typing import Any, Dict, List, Tuple


INDEX_BACKEND = (os.getenv("INDEX_BACKEND", "keyword").strip().lower() or "keyword")
KEYWORD_INDEX_PATH = Path(os.getenv("KEYWORD_INDEX_PATH", "data/chroma_db/keyword_chunks.json"))


def get_active_index_backend() -> str:
    """Return the currently configured index backend name."""
    return INDEX_BACKEND


def get_index_backend_notice() -> str:
    """Return a short user-facing note about the active backend."""
    if INDEX_BACKEND == "keyword":
        return (
            "Using the safe keyword-search backend. "
            "Semantic vector search is disabled to avoid Python runtime crashes in this environment."
        )
    return f"Using index backend: {INDEX_BACKEND}"


def _normalize_text(text: str) -> str:
    return re.sub(r"\s+", " ", str(text or "")).strip().lower()


def _tokenize(text: str) -> List[str]:
    return re.findall(r"[a-z0-9]{2,}", _normalize_text(text))


def _load_keyword_rows() -> List[Dict[str, Any]]:
    if not KEYWORD_INDEX_PATH.exists():
        return []
    with open(KEYWORD_INDEX_PATH, "r", encoding="utf-8") as handle:
        data = json.load(handle)
    if not isinstance(data, list):
        return []
    return [row for row in data if isinstance(row, dict)]


def _save_keyword_rows(rows: List[Dict[str, Any]]) -> None:
    KEYWORD_INDEX_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(KEYWORD_INDEX_PATH, "w", encoding="utf-8") as handle:
        json.dump(rows, handle, ensure_ascii=False, indent=2)


def _keyword_index_row(chunk: Dict[str, Any]) -> Dict[str, Any]:
    text = str(chunk.get("text", "") or "")
    return {
        "chunk_id": str(chunk.get("chunk_id", "") or ""),
        "doc_id": str(chunk.get("doc_id", "") or ""),
        "doc_title": str(chunk.get("doc_title", "") or ""),
        "page": chunk.get("page", ""),
        "text": text,
        "normalized_text": _normalize_text(text),
        "tokens": _tokenize(text),
    }


def _score_keyword_match(query_tokens: List[str], row: Dict[str, Any]) -> float:
    if not query_tokens:
        return 0.0

    row_tokens = row.get("tokens", [])
    if not isinstance(row_tokens, list) or not row_tokens:
        return 0.0

    row_token_set = set(str(token) for token in row_tokens)
    query_token_set = set(query_tokens)
    overlap = len(query_token_set & row_token_set)
    if overlap == 0:
        return 0.0

    normalized_query = " ".join(query_tokens)
    phrase_bonus = 0.25 if normalized_query and normalized_query in row.get("normalized_text", "") else 0.0
    return (overlap / math.sqrt(max(len(query_token_set), 1) * max(len(row_token_set), 1))) + phrase_bonus


def index_chunks(chunks: List[Dict[str, Any]]) -> Tuple[int, int]:
    """Persist chunks into the lightweight keyword index."""
    existing_rows = _load_keyword_rows()
    existing_ids = {str(row.get("chunk_id", "")).strip() for row in existing_rows}

    added = 0
    skipped = 0

    for chunk in chunks:
        if not isinstance(chunk, dict):
            skipped += 1
            continue

        chunk_id = str(chunk.get("chunk_id", "")).strip()
        if not chunk_id or chunk_id in existing_ids:
            skipped += 1
            continue

        existing_rows.append(_keyword_index_row(chunk))
        existing_ids.add(chunk_id)
        added += 1

    _save_keyword_rows(existing_rows)
    return added, skipped


def query_index(query: str, top_k: int = 8) -> Dict[str, List[List[Any]]]:
    """Search the keyword index and return a Chroma-like result structure."""
    query_tokens = _tokenize(query)
    if not query_tokens:
        return {"ids": [[]], "documents": [[]], "metadatas": [[]], "distances": [[]]}

    rows = _load_keyword_rows()
    if not rows:
        return {"ids": [[]], "documents": [[]], "metadatas": [[]], "distances": [[]]}

    scored_rows = []
    for row in rows:
        score = _score_keyword_match(query_tokens, row)
        if score <= 0:
            continue
        scored_rows.append((score, row))

    scored_rows.sort(
        key=lambda item: (
            -item[0],
            str(item[1].get("doc_title", "")),
            str(item[1].get("chunk_id", "")),
        )
    )

    top_rows = [row for _, row in scored_rows[: max(top_k, 0)]]

    return {
        "ids": [[row.get("chunk_id", "") for row in top_rows]],
        "documents": [[row.get("text", "") for row in top_rows]],
        "metadatas": [[
            {
                "doc_id": row.get("doc_id", ""),
                "doc_title": row.get("doc_title", ""),
                "page": row.get("page", ""),
            }
            for row in top_rows
        ]],
        "distances": [[round(max(0.0, 1.0 - _score_keyword_match(query_tokens, row)), 6) for row in top_rows]],
    }
