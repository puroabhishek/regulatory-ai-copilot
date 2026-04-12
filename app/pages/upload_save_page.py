"""Streamlit page for PDF upload and page extraction."""

import streamlit as st

from orchestrators.regulation_workflow import prepare_uploaded_regulation_pages, persist_extracted_pages


def render_upload_save_page() -> None:
    """Render the upload-and-save workflow for text-based PDFs."""
    st.header("Regulation Upload")
    st.caption("Advanced workspace: upload a text-based regulation PDF, extract the text, and save it for downstream indexing or control extraction.")
    uploaded = st.file_uploader("Upload a PDF", type=["pdf"], key="upload_pdf")

    if not uploaded:
        return

    with st.spinner("Extracting text from PDF..."):
        result = prepare_uploaded_regulation_pages(uploaded, file_type="pdf")
        pages = result.get("pages", [])

    total_chars = result.get("total_chars", 0)
    for warning in result.get("warnings", []):
        st.warning(warning)

    if total_chars < 200:
        st.error("This looks like a scanned PDF. Use a text-based PDF for now.")
    else:
        st.success("Text extracted successfully.")

    st.write(f"Pages extracted: **{len(pages)}** | Total characters: **{total_chars}**")

    st.subheader("Preview (first 2 pages)")
    for page in pages[:2]:
        st.markdown(f"### Page {page['page']}")
        st.text(page["text"][:2000] if page.get("text") else "[No text extracted]")

    if st.button("Save extracted text", key="save_extracted"):
        saved_path = persist_extracted_pages(
            pages=pages,
            doc_id=result.get("doc_id", ""),
            doc_title=result.get("doc_title", ""),
        )
        st.success(f"Saved: {saved_path}")
