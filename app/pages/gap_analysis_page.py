"""Streamlit page renderer for policy gap analysis.

This module owns input collection and output rendering for the gap-analysis
experience. Workflow sequencing and analysis logic live in the orchestrator and
domain layers.
"""

import json
from pathlib import Path
from typing import Iterable, List, Optional

import pandas as pd
import streamlit as st

from orchestrators.gap_workflow import (
    list_gap_control_files,
    list_gap_profile_files,
    parse_gap_policy_file,
    run_gap_workflow,
    save_gap_analysis_csv,
    save_gap_analysis_json,
    save_gap_run_metadata,
)


DATA_DIR = Path("data")
CONTROLS_DIR = DATA_DIR / "controls"
PROFILES_DIR = DATA_DIR / "profiles"
GAP_ANALYSIS_DIR = DATA_DIR / "gap_analysis"

SUPPORTED_POLICY_FILE_TYPES = ["txt", "md", "pdf", "docx"]


def _list_control_files() -> List[str]:
    return list_gap_control_files(str(CONTROLS_DIR))


def _list_profile_files() -> List[str]:
    return list_gap_profile_files(str(PROFILES_DIR))


@st.cache_data(show_spinner=False)
def _read_policy_file(file_bytes: bytes, file_name: str) -> dict:
    """Parse an uploaded policy file via the shared ingestion layer."""
    return parse_gap_policy_file(file_bytes=file_bytes, file_name=file_name)


def _safe_summary_value(summary: dict, *keys: str, default=0):
    for key in keys:
        if key in summary:
            return summary.get(key, default)
    return default


def _build_summary_cards(summary: dict) -> None:
    total_controls = _safe_summary_value(summary, "total_controls", "total_reviewed", default=0)
    covered = _safe_summary_value(summary, "covered", default=0)
    partial = _safe_summary_value(summary, "partially_covered", "partial", default=0)
    missing = _safe_summary_value(summary, "missing", default=0)

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Total Controls", total_controls)
    c2.metric("Covered", covered)
    c3.metric("Partial", partial)
    c4.metric("Missing", missing)


def _build_run_header(summary: dict, used_control_files: list, new_control_files_created: list) -> None:
    total = max(_safe_summary_value(summary, "total_controls", "total_reviewed", default=0), 1)
    covered = _safe_summary_value(summary, "covered", default=0)
    partial = _safe_summary_value(summary, "partially_covered", "partial", default=0)
    missing = _safe_summary_value(summary, "missing", default=0)

    compliance_score = round(((covered + (0.5 * partial)) / total) * 100, 1)

    if missing >= max(5, total * 0.2):
        risk_label = "High"
        risk_emoji = "🔴"
    elif (partial + missing) >= max(5, total * 0.25):
        risk_label = "Medium"
        risk_emoji = "🟡"
    else:
        risk_label = "Low"
        risk_emoji = "🟢"

    left, right = st.columns([2, 1])

    with left:
        st.markdown("## Output")
        st.markdown(
            f"""
**Compliance Score:** {compliance_score}%  
**Risk Indicator:** {risk_emoji} {risk_label}
"""
        )

    with right:
        st.info(
            f"Used controls: {len(used_control_files)}\n\n"
            f"New controls created: {len(new_control_files_created)}"
        )


def _normalize_gap_rows(gap_rows: list) -> pd.DataFrame:
    df = pd.DataFrame(gap_rows or [])
    if df.empty:
        return df

    rename_map = {
        "control_id": "Control ID",
        "control_title": "Control",
        "title": "Control",
        "control_name": "Control",
        "statement": "Control",
        "control_text": "Control Text",
        "text": "Control Text",
        "status": "Status",
        "coverage_status": "Status",
        "reason": "Reason",
        "gap_reason": "Reason",
        "remediation": "Remediation",
        "suggested_remediation": "Remediation",
        "severity": "Severity",
        "source_file": "Source File",
        "source_doc_title": "Source Document",
        "regulation": "Regulation",
        "domain": "Domain",
    }

    df = df.rename(columns={key: value for key, value in rename_map.items() if key in df.columns})

    if "Status" in df.columns:
        df["Status"] = df["Status"].replace(
            {
                "covered": "Covered",
                "partially_covered": "Partial",
                "partially covered": "Partial",
                "partial": "Partial",
                "missing": "Missing",
            }
        )

    for col in [
        "Control ID",
        "Control",
        "Control Text",
        "Status",
        "Reason",
        "Remediation",
        "Severity",
        "Source File",
        "Source Document",
        "Regulation",
        "Domain",
    ]:
        if col not in df.columns:
            df[col] = ""

    display_cols = [
        "Control ID",
        "Control",
        "Status",
        "Severity",
        "Reason",
        "Remediation",
        "Source Document",
        "Source File",
        "Regulation",
        "Domain",
        "Control Text",
    ]
    return df[display_cols]


def _render_detail_panel(df: pd.DataFrame) -> None:
    st.markdown("### Gap Detail")

    option_labels = [
        f"{row.get('Control ID', 'NA')} · {row.get('Status', '')} · {str(row.get('Control', ''))[:80]}"
        for _, row in df.iterrows()
    ]

    if not option_labels:
        st.info("No controls available for detail view.")
        return

    selected_label = st.selectbox("Select a control", options=option_labels, key="gap_detail_select")
    selected_idx = option_labels.index(selected_label)
    row = df.iloc[selected_idx]

    st.markdown(f"**Control ID:** {row.get('Control ID', '')}")
    st.markdown(f"**Status:** {row.get('Status', '')}")

    if str(row.get("Severity", "")).strip():
        st.markdown(f"**Severity:** {row.get('Severity', '')}")
    if str(row.get("Regulation", "")).strip():
        st.markdown(f"**Regulation:** {row.get('Regulation', '')}")
    if str(row.get("Domain", "")).strip():
        st.markdown(f"**Domain:** {row.get('Domain', '')}")
    if str(row.get("Source Document", "")).strip():
        st.markdown(f"**Source Document:** {row.get('Source Document', '')}")

    st.markdown("**Control**")
    st.write(row.get("Control", "") or row.get("Control Text", ""))

    st.markdown("**Reason**")
    st.write(row.get("Reason", ""))

    st.markdown("**Suggested remediation**")
    st.write(row.get("Remediation", ""))

    st.divider()
    c1, c2 = st.columns(2)
    c1.button("Create Task", disabled=True, help="Next module: Gap -> Action Engine")
    c2.button("Assign Owner", disabled=True, help="Will plug into Compliance Cockpit")


def _render_control_source_selector() -> tuple[str, list[str], list]:
    st.markdown("## Step 1 - Select Regulation Source")

    control_mode_label = st.radio(
        "Choose control source",
        options=["Use existing controls", "Upload new regulations"],
        horizontal=True,
        key="gap_control_source_mode",
    )

    control_source_mode = "existing" if control_mode_label == "Use existing controls" else "upload_new"
    selected_control_files: list[str] = []
    uploaded_regulation_files: list = []

    if control_source_mode == "existing":
        available_controls = _list_control_files()
        selected_control_files = st.multiselect(
            "Select control sets",
            options=available_controls,
            help="These are already processed control JSON files from data/controls.",
            key="gap_selected_control_files",
        )
        if selected_control_files:
            st.success(f"Selected {len(selected_control_files)} control file(s).")
        else:
            st.info("Choose one or more control files.")
    else:
        uploaded_regulation_files = st.file_uploader(
            "Upload new regulation PDFs",
            type=["pdf"],
            accept_multiple_files=True,
            help="These files will be processed inline during this run.",
            key="gap_uploaded_regulation_files",
        )
        if uploaded_regulation_files:
            st.success(f"Uploaded {len(uploaded_regulation_files)} PDF(s).")
        else:
            st.info("Upload one or more regulation PDFs.")

    return control_source_mode, selected_control_files, uploaded_regulation_files


def _render_policy_input() -> str:
    st.markdown("## Step 2 - Provide Policy / Current State")

    policy_input_mode = st.radio(
        "Policy source",
        options=["Paste policy text", "Upload policy file (.txt/.md/.pdf/.docx)"],
        horizontal=True,
        key="gap_policy_input_mode",
    )

    if policy_input_mode == "Paste policy text":
        return st.text_area(
            "Paste policy text",
            height=240,
            placeholder="Paste current policy / SOP / current-state narrative here...",
            key="gap_policy_text_area",
        )

    policy_file = st.file_uploader(
        "Upload policy file",
        type=SUPPORTED_POLICY_FILE_TYPES,
        accept_multiple_files=False,
        help="Supported: .txt, .md, .pdf, .docx",
        key="gap_policy_file_uploader",
    )

    policy_text = ""
    if policy_file is not None:
        try:
            parsed_policy = _read_policy_file(policy_file.getvalue(), policy_file.name)
            policy_text = parsed_policy.get("cleaned_text") or parsed_policy.get("extracted_text", "")
            for warning in parsed_policy.get("warnings", []):
                st.warning(warning)
            st.text_area("Loaded policy text", value=policy_text, height=240, key="gap_loaded_policy_text")
        except Exception as exc:
            st.error(str(exc))

    return policy_text


def _render_run_configuration() -> tuple[Optional[str], int, bool]:
    st.markdown("## Step 3 - Run Configuration")

    profiles = _list_profile_files()
    if not profiles:
        st.info("No business profiles found yet. Create one in Tab 4 first.")
        profile_name = None
    else:
        profile_name = st.selectbox(
            "Business profile",
            options=profiles,
            help="Required to map controls into company context.",
            key="gap_profile_name",
        )

    max_controls = st.number_input(
        "Max controls",
        min_value=1,
        max_value=5000,
        value=200,
        step=10,
        key="gap_max_controls",
    )

    run_clicked = st.button("Run Gap Analysis", type="primary", use_container_width=True, key="gap_run_button")
    return profile_name, max_controls, run_clicked


def _validate_run_inputs(
    profile_name: Optional[str],
    control_source_mode: str,
    selected_control_files: Iterable[str],
    uploaded_regulation_files: Iterable,
    policy_text: str,
) -> list[str]:
    errors: list[str] = []

    if not profile_name:
        errors.append("Select a business profile.")
    if control_source_mode == "existing" and not list(selected_control_files):
        errors.append("Select at least one existing control file.")
    if control_source_mode == "upload_new" and not list(uploaded_regulation_files):
        errors.append("Upload at least one regulation PDF.")
    if not policy_text.strip():
        errors.append("Provide policy text to analyse.")

    return errors


def _run_gap_analysis(
    profile_name: str,
    policy_text: str,
    control_source_mode: str,
    selected_control_files: list[str],
    uploaded_regulation_files: list,
    max_controls: int,
    default_model=None,
) -> dict:
    return run_gap_workflow(
        profile_name=profile_name,
        profiles_dir=str(PROFILES_DIR),
        policy_text=policy_text,
        control_source_mode=control_source_mode,
        selected_control_files=selected_control_files,
        uploaded_regulation_files=uploaded_regulation_files,
        model=default_model,
        max_controls=max_controls,
    )


def _render_gap_register(df: pd.DataFrame) -> pd.DataFrame:
    st.markdown("## Gap Register")

    f1, f2 = st.columns(2)
    with f1:
        status_options = sorted(value for value in df["Status"].dropna().unique() if str(value).strip())
        status_filter = st.multiselect("Filter by status", options=status_options, key="gap_status_filter")
    with f2:
        severity_options = sorted(value for value in df["Severity"].dropna().unique() if str(value).strip())
        severity_filter = st.multiselect("Filter by severity", options=severity_options, key="gap_severity_filter")

    filtered_df = df.copy()
    if status_filter:
        filtered_df = filtered_df[filtered_df["Status"].isin(status_filter)]
    if severity_filter:
        filtered_df = filtered_df[filtered_df["Severity"].isin(severity_filter)]

    st.dataframe(
        filtered_df[
            [column for column in ["Control ID", "Control", "Status", "Severity", "Reason", "Remediation"] if column in filtered_df.columns]
        ],
        use_container_width=True,
        height=420,
    )

    left, right = st.columns([1.4, 1])
    with left:
        st.markdown("## Priority Views")
        missing_df = filtered_df[filtered_df["Status"] == "Missing"] if "Status" in filtered_df.columns else pd.DataFrame()
        partial_df = filtered_df[filtered_df["Status"] == "Partial"] if "Status" in filtered_df.columns else pd.DataFrame()

        if not missing_df.empty:
            st.markdown("### Missing Controls")
            st.dataframe(
                missing_df[[column for column in ["Control ID", "Control", "Severity", "Remediation"] if column in missing_df.columns]],
                use_container_width=True,
                height=220,
            )
        if not partial_df.empty:
            st.markdown("### Partial Controls")
            st.dataframe(
                partial_df[[column for column in ["Control ID", "Control", "Severity", "Remediation"] if column in partial_df.columns]],
                use_container_width=True,
                height=220,
            )
    with right:
        _render_detail_panel(filtered_df if not filtered_df.empty else df)

    return filtered_df


def _render_export_section(result: dict, gap_rows: list, filtered_df: pd.DataFrame, run_metadata: dict) -> None:
    st.markdown("## Save & Export")

    GAP_ANALYSIS_DIR.mkdir(parents=True, exist_ok=True)

    default_run_name = run_metadata.get("run_id", "gap_analysis_run")
    run_name = st.text_input("Run name", value=default_run_name, key="gap_run_name")

    c1, c2, c3 = st.columns(3)

    with c1:
        if st.button("Save Run Metadata", use_container_width=True, key="gap_save_run_metadata"):
            meta_path = str(GAP_ANALYSIS_DIR / f"{run_name}_metadata.json")
            save_gap_run_metadata(run_metadata, meta_path)
            st.success("Run metadata saved.")

    result_json_bytes = json.dumps(result, indent=2, default=str).encode("utf-8")
    with c2:
        st.download_button(
            "Download Result JSON",
            data=result_json_bytes,
            file_name=f"{run_name}.json",
            mime="application/json",
            use_container_width=True,
            key="gap_download_json",
        )

    csv_bytes = filtered_df.to_csv(index=False).encode("utf-8")
    with c3:
        st.download_button(
            "Download Gap CSV",
            data=csv_bytes,
            file_name=f"{run_name}.csv",
            mime="text/csv",
            use_container_width=True,
            key="gap_download_csv",
        )

    st.caption("Optional persistence into data/gap_analysis")
    p1, p2 = st.columns(2)

    with p1:
        if st.button("Persist JSON to data/gap_analysis", use_container_width=True, key="gap_persist_json"):
            json_path = str(GAP_ANALYSIS_DIR / f"{run_name}.json")
            save_gap_analysis_json(gap_rows, json_path)
            st.success("Gap analysis JSON saved.")

    with p2:
        if st.button("Persist CSV to data/gap_analysis", use_container_width=True, key="gap_persist_csv"):
            csv_path = str(GAP_ANALYSIS_DIR / f"{run_name}.csv")
            save_gap_analysis_csv(filtered_df.to_dict(orient="records"), csv_path)
            st.success("Gap analysis CSV saved.")


def render_gap_analysis_page(default_model=None) -> None:
    """Render the gap-analysis page while delegating workflow logic outward."""
    st.header("Tab 8 · Gap Analyzer")
    st.caption("Run a policy-vs-regulation gap analysis using existing controls or newly uploaded regulation PDFs.")

    if "gap_run_result" not in st.session_state:
        st.session_state["gap_run_result"] = None

    control_source_mode, selected_control_files, uploaded_regulation_files = _render_control_source_selector()
    st.divider()

    policy_text = _render_policy_input()
    st.divider()

    profile_name, max_controls, run_clicked = _render_run_configuration()

    if run_clicked:
        errors = _validate_run_inputs(
            profile_name=profile_name,
            control_source_mode=control_source_mode,
            selected_control_files=selected_control_files,
            uploaded_regulation_files=uploaded_regulation_files,
            policy_text=policy_text,
        )

        if errors:
            for error in errors:
                st.error(error)
        else:
            with st.spinner("Running gap analysis workflow..."):
                st.session_state["gap_run_result"] = _run_gap_analysis(
                    profile_name=profile_name,
                    policy_text=policy_text,
                    control_source_mode=control_source_mode,
                    selected_control_files=selected_control_files,
                    uploaded_regulation_files=uploaded_regulation_files,
                    max_controls=max_controls,
                    default_model=default_model,
                )

    result = st.session_state.get("gap_run_result")
    if not result:
        return

    gap_rows = result.get("gap_rows", [])
    summary = result.get("summary", {})
    used_control_files = result.get("used_control_files", [])
    new_control_files_created = result.get("new_control_files_created", [])
    run_metadata = result.get("run_metadata", {})

    st.divider()
    _build_run_header(summary, used_control_files, new_control_files_created)
    _build_summary_cards(summary)

    df = _normalize_gap_rows(gap_rows)
    if df.empty:
        st.info("The run completed, but there were no gap rows to display.")
        return

    filtered_df = _render_gap_register(df)
    _render_export_section(result=result, gap_rows=gap_rows, filtered_df=filtered_df, run_metadata=run_metadata)


render_gap_analyzer_tab_v2 = render_gap_analysis_page
render_gap_analyzer_tab = render_gap_analysis_page
