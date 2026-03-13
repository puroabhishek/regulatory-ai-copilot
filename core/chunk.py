import json
from typing import List, Dict, Any
import tiktoken


def load_pages_jsonl(path: str) -> List[Dict[str, Any]]:
    """Read saved pages JSONL into memory."""
    pages = []
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            pages.append(json.loads(line))
    return pages


def chunk_text(
    text: str,
    chunk_tokens: int = 900,
    overlap_tokens: int = 200,
    model_for_tokens: str = "gpt-4o-mini",
) -> List[str]:
    """
    What it does:
    - Splits text into overlapping token chunks.
    Why:
    - Smaller chunks improve retrieval accuracy and reduce hallucinations.
    """
    enc = tiktoken.encoding_for_model(model_for_tokens)

    tokens = enc.encode(text)
    if not tokens:
        return []

    chunks = []
    start = 0
    while start < len(tokens):
        end = min(start + chunk_tokens, len(tokens))
        chunk = enc.decode(tokens[start:end]).strip()
        if chunk:
            chunks.append(chunk)
        if end == len(tokens):
            break
        start = max(0, end - overlap_tokens)

    return chunks


def pages_to_chunks(
    pages: List[Dict[str, Any]],
    chunk_tokens: int = 900,
    overlap_tokens: int = 200,
) -> List[Dict[str, Any]]:
    """
    Converts page-level records into chunk-level records with provenance (doc_id, page).
    """
    out = []
    for p in pages:
        page_text = p.get("text", "")
        parts = chunk_text(page_text, chunk_tokens=chunk_tokens, overlap_tokens=overlap_tokens)
        for idx, part in enumerate(parts, start=1):
            out.append(
                {
                    "chunk_id": f"{p['doc_id']}_p{p['page']}_c{idx}",
                    "doc_id": p["doc_id"],
                    "doc_title": p["doc_title"],
                    "page": p["page"],
                    "text": part,
                }
            )
    return out