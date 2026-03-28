"""Streamlit page for chunking, indexing, and semantic search."""

from pathlib import Path

import streamlit as st

from orchestrators.regulation_workflow import (
    build_index_for_processed_file,
    get_index_status,
    list_processed_page_files,
    search_processed_index,
)


def render_index_search_page() -> None:
    """Render the indexing and semantic-search workflow."""
    index_status = get_index_status()
    st.write("Index saved JSONL files -> search stored chunks.")
    st.caption(f"Index backend: `{index_status['backend']}`")
    st.info(index_status["notice"])

    processed_dir = Path("data/processed")
    files = list_processed_page_files(str(processed_dir))

    if not files:
        st.info("No processed files yet. Go to Tab 1 and save a PDF first.")
        return

    selected = st.selectbox("Select a processed JSONL file", files, key="index_select")
    chunk_tokens = st.slider("Chunk size (tokens)", 300, 1500, 900, 100, key="chunk_tokens")
    overlap_tokens = st.slider("Overlap (tokens)", 0, 400, 200, 50, key="overlap_tokens")
    top_k = st.slider("Top-K results", 3, 20, 8, 1, key="top_k")

    if st.button("Build / Update Index", key="build_index"):
        try:
            with st.spinner("Chunking pages..."):
                workflow_result = build_index_for_processed_file(
                    selected_file=selected,
                    chunk_tokens=chunk_tokens,
                    overlap_tokens=overlap_tokens,
                    processed_dir=str(processed_dir),
                )
            st.success(
                f"Index updated. Added: {workflow_result['added']}, Skipped: {workflow_result['skipped']}"
            )
        except Exception as exc:
            st.exception(exc)

    st.divider()
    st.subheader("Search")
    query = st.text_input("Your question", value="", key="search_q")

    if st.button("Search", key="search_btn"):
        try:
            if not query.strip():
                st.warning("Please enter a question.")
                return

            search_result = search_processed_index(query.strip(), top_k=top_k)
            result = search_result["result"]

            if not result["ids"] or not result["ids"][0]:
                st.info("No matching indexed chunks found. Try building the index first or rephrasing the query.")
                return

            st.subheader("Answer (Checklist)")
            requirements = search_result["requirements"]

            if not requirements:
                st.info("No requirement-like lines found. Try another question.")
            else:
                for idx, item in enumerate(requirements, start=1):
                    st.write(f"{idx}. {item}")

        except Exception as exc:
            st.exception(exc)
