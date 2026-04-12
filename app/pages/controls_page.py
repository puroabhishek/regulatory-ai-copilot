"""Streamlit page for extracting controls from processed regulations."""

import streamlit as st

from orchestrators.control_workflow import (
    extract_controls_from_processed_file,
    list_extracted_control_files,
    list_processed_regulation_files,
)


def render_controls_page() -> None:
    """Render the controls extraction workflow."""
    st.header("Controls")
    st.caption("Advanced workspace: extract control points from saved regulation documents and persist them as JSON/CSV.")
    st.caption("Classification model is resolved centrally by the backend configuration.")

    files = list_processed_regulation_files()

    if not files:
        st.info("No processed files yet. Go to Regulation Upload and save a PDF first.")
        return

    selected = st.selectbox("Select a processed JSONL file", files, key="controls_select")
    prefix = st.text_input("Control ID prefix", value="QCB-CCR", key="controls_prefix")
    min_len = st.slider("Minimum sentence length", 30, 200, 60, 10, key="controls_minlen")
    max_len = st.slider("Maximum sentence length", 200, 1500, 500, 50, key="controls_maxlen")

    if st.button("Extract Controls", key="extract_controls_btn"):
        try:
            with st.spinner("Extracting and classifying controls..."):
                result = extract_controls_from_processed_file(
                    selected_file=selected,
                    prefix=prefix,
                    min_len=min_len,
                    max_len=max_len,
                    model=None,
                )
                controls = result["controls"]

            st.success(f"Controls extracted successfully: {len(controls)} controls")
            st.info(f"Added to controls master registry: {result['added_to_master']}")
            st.info(f"Time taken: {result['elapsed_seconds']} seconds")
            st.code(result["out_json"])
            st.code(result["out_csv"])

            if controls:
                preview_rows = []
                for control in controls[:10]:
                    preview_rows.append(
                        {
                            "control_id": control.get("control_id", ""),
                            "statement": control.get("statement", ""),
                            "category": control.get("category", ""),
                            "severity": control.get("severity", ""),
                            "policy_tags": ", ".join(control.get("policy_tags", []))
                            if isinstance(control.get("policy_tags"), list)
                            else control.get("policy_tags", ""),
                        }
                    )
                st.dataframe(preview_rows, use_container_width=True)
            else:
                st.warning("No controls were extracted from this document.")

        except Exception as exc:
            st.exception(exc)

    st.divider()
    st.subheader("Available extracted control files")
    control_files = list_extracted_control_files()
    if control_files:
        st.write(control_files)
    else:
        st.caption("No controls files available yet.")
