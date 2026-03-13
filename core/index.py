import os
from typing import List, Dict, Any, Tuple

import chromadb
from chromadb.config import Settings
from sentence_transformers import SentenceTransformer


# Load embedding model once (global cache)
_embedding_model = None


def get_embedding_model(model_name: str = "all-MiniLM-L6-v2"):
    """
    Loads local embedding model once.
    Why:
    - Avoids reloading model on every request.
    """
    global _embedding_model
    if _embedding_model is None:
        _embedding_model = SentenceTransformer(model_name)
    return _embedding_model


def embed_texts(texts: List[str]) -> List[List[float]]:
    """
    What it does:
    - Converts text into vector embeddings locally.
    Why:
    - Enables semantic search without API cost.
    """
    model = get_embedding_model()
    vectors = model.encode(texts, normalize_embeddings=True)
    return vectors.tolist()


def get_chroma_collection(
    persist_dir: str = "data/chroma_db",
    name: str = "regulatory_docs"
):
    client = chromadb.PersistentClient(
        path=persist_dir,
        settings=Settings(anonymized_telemetry=False)
    )
    return client.get_or_create_collection(name=name)


def index_chunks(chunks: List[Dict[str, Any]]) -> Tuple[int, int]:
    """
    Adds chunks to Chroma vector DB.
    """
    col = get_chroma_collection()

    texts = [c["text"] for c in chunks]
    embeddings = embed_texts(texts)

    ids = [c["chunk_id"] for c in chunks]
    metadatas = [
        {
            "doc_id": c["doc_id"],
            "doc_title": c["doc_title"],
            "page": c["page"]
        }
        for c in chunks
    ]

    col.add(
        ids=ids,
        documents=texts,
        metadatas=metadatas,
        embeddings=embeddings
    )

    return (len(chunks), 0)


def query_index(query: str, top_k: int = 8):
    """
    Semantic search: query -> nearest chunks.
    """
    col = get_chroma_collection()

    q_emb = embed_texts([query])[0]

    res = col.query(
        query_embeddings=[q_emb],
        n_results=top_k,
        include=["documents", "metadatas", "distances"]
    )

    return res