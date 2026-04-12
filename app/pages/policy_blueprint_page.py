"""Streamlit page for profile-led policy creation from scratch."""

from pathlib import Path

import streamlit as st

from orchestrators.policy_workflow import (
    build_policy_profile_context,
    create_policy_from_scratch,
    list_available_blueprints,
    list_policy_blueprint_inputs,
    load_reference_policy_text,
    save_reference_policy_text,
)


def render_policy_blueprint_page() -> None:
    """Render the policy generator workflow."""
    st.header("Policy Generator")
    st.caption("Create a policy from scratch using the saved business profile and the regulations or guidelines that apply to that business.")

    page_inputs = list_policy_blueprint_inputs()
    controls_files = page_inputs["control_files"]
    profile_files = page_inputs["profile_files"]
    reference_files = page_inputs["reference_files"]
    regulation_catalog = page_inputs["regulation_catalog"]
    catalog_rows = {item["title"]: item for item in regulation_catalog}

    if not profile_files:
        st.info("No business profiles found yet. Create one in the Business Profile tab first.")
        return

    selected_profile = st.selectbox("Business profile", profile_files, key="policy_profile_select")
    profile_context = build_policy_profile_context(selected_profile)
    profile_data = profile_context["profile"]

    if st.session_state.get("policy_profile_seed") != selected_profile:
        st.session_state["policy_selected_regulations"] = profile_context["default_regulations"]
        st.session_state["policy_profile_seed"] = selected_profile
        st.session_state["policy_generation_result"] = None

    top_left, top_right = st.columns([1.2, 1])

    with top_left:
        st.markdown("### Policy details")
        policy_name = st.text_input("Policy name", value="Data Protection and Privacy Policy", key="policy_name")
        policy_context = st.text_area(
            "Business and policy context",
            value="This policy should reflect the company's operating model, outsourced dependencies, cloud footprint, and regulatory obligations.",
            height=140,
            key="policy_context",
        )
        drafting_instructions = st.text_area(
            "Drafting instructions",
            value="Use a formal policy structure. Keep it business-specific, practical, and aligned to the selected regulations.",
            key="policy_instructions",
            height=140,
        )

    with top_right:
        st.markdown("### Profile summary")
        st.json(
            {
                "profile_name": profile_data.get("profile_name", ""),
                "country": profile_data.get("country", ""),
                "regulator": profile_data.get("regulator", ""),
                "sector": profile_data.get("sector", ""),
                "business_type": profile_data.get("business_type", ""),
                "cloud_use": profile_data.get("cloud_use", ""),
                "handles_pii": profile_data.get("handles_pii", ""),
                "applicable_regulations": profile_context["default_regulations"],
            }
        )

    st.markdown("### Applicable regulations and guidelines")
    st.multiselect(
        "Select the regulations or guidelines the generator should consider",
        options=list(catalog_rows.keys()),
        key="policy_selected_regulations",
        help="This defaults to the regulations stored with the selected business profile.",
    )

    selected_regulations = st.session_state.get("policy_selected_regulations", [])
    if selected_regulations:
        regulation_preview_rows = []
        for title in selected_regulations:
            entry = catalog_rows.get(title, {})
            regulation_preview_rows.append(
                {
                    "Regulation / Guideline": title,
                    "Type": entry.get("kind", "Custom"),
                    "Ready in system": "Yes" if entry.get("control_file_available") else "Upload needed",
                    "Summary": entry.get("summary", ""),
                }
            )
        st.dataframe(regulation_preview_rows, use_container_width=True, hide_index=True)
    else:
        st.info("Select at least one applicable regulation or upload regulation PDFs below.")

    st.markdown("### Regulation sources")
    uploaded_regulation_files = st.file_uploader(
        "Upload regulation PDFs to include in this policy run (optional)",
        type=["pdf"],
        accept_multiple_files=True,
        key="policy_uploaded_regulations",
        help="Use this when a selected regulation is not yet available in the local control library, or when you want to add an extra guideline.",
    )

    with st.expander("Advanced options"):
        additional_control_files = st.multiselect(
            "Additional existing control files to include",
            options=controls_files,
            key="policy_additional_control_files",
            help="This preserves the current advanced capability of selecting control files directly.",
        )

        st.markdown("#### Optional reference policy")
        reference_choice = st.selectbox(
            "Choose existing reference policy",
            ["(none)"] + reference_files,
            key="policy_ref_select",
        )

        sample_policy_text = ""
        if reference_choice != "(none)":
            sample_policy_text = load_reference_policy_text(reference_choice)

        sample_policy_text = st.text_area(
            "Reference policy text / expected output style (editable)",
            value=sample_policy_text,
            key="policy_sample_policy_text",
            height=220,
        )

        new_ref_name = st.text_input("Save this reference text as (optional name)", value="", key="policy_new_ref_name")
        if st.button("Save reference policy text", key="policy_save_ref_btn"):
            if new_ref_name.strip() and sample_policy_text.strip():
                saved_ref = save_reference_policy_text(new_ref_name.strip(), sample_policy_text.strip())
                st.success(f"Saved reference: {saved_ref}")
            else:
                st.warning("Enter a reference name and text first.")

    if st.button("Generate Policy From Scratch", key="policy_generate_btn", type="primary", use_container_width=True):
        try:
            with st.spinner("Identifying regulations, deriving controls, and drafting the policy..."):
                st.session_state["policy_generation_result"] = create_policy_from_scratch(
                    policy_name=policy_name,
                    policy_context=policy_context,
                    selected_profile_file=selected_profile,
                    selected_regulations=selected_regulations,
                    sample_policy_text=sample_policy_text,
                    drafting_instructions=drafting_instructions,
                    uploaded_regulation_files=uploaded_regulation_files,
                    additional_control_files=additional_control_files,
                    model=None,
                )
        except Exception as exc:
            st.exception(exc)

    result = st.session_state.get("policy_generation_result")
    if result:
        st.divider()
        st.markdown("### Output")
        st.success("Policy draft created successfully.")

        if result.get("missing_regulations"):
            st.warning(
                "Some selected regulations are not yet mapped to local control files. "
                f"Upload those documents if you want them included directly: {', '.join(result['missing_regulations'])}"
            )

        summary_left, summary_right = st.columns([1, 1])
        with summary_left:
            st.metric("Controls considered", len(result.get("merged_controls", [])))
            st.metric("Control files used", len(result.get("used_control_files", [])))
        with summary_right:
            st.code(result["blueprint_path"])
            st.code(result["policy_path"])

        with st.expander("Preview policy draft", expanded=True):
            st.markdown(result["policy_md"])

        with open(result["policy_path"], "rb") as handle:
            st.download_button(
                label="Download Policy Draft (.md)",
                data=handle,
                file_name=Path(result["policy_path"]).name,
                mime="text/markdown",
                key="policy_download_md",
            )

        st.caption("The reusable blueprint was saved automatically. Continue in Policy Implementation when you want implementation plans, audit registers, and traceability outputs.")

    st.divider()
    st.subheader("Existing blueprints")
    existing_blueprints = list_available_blueprints()
    if existing_blueprints:
        st.write(existing_blueprints)
    else:
        st.caption("No blueprints saved yet.")
