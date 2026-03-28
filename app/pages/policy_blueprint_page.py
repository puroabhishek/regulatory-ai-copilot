"""Streamlit page for creating policy blueprints."""

import streamlit as st

from orchestrators.policy_workflow import (
    create_policy_blueprint,
    list_available_blueprints,
    list_policy_blueprint_inputs,
    load_reference_policy_text,
    save_reference_policy_text,
)


def render_policy_blueprint_page() -> None:
    """Render the blueprint authoring workflow."""
    st.write("Create a **Policy Blueprint** using selected controls, business profile, and optional sample policy text.")

    page_inputs = list_policy_blueprint_inputs()
    controls_files = page_inputs["control_files"]
    profile_files = page_inputs["profile_files"]
    reference_files = page_inputs["reference_files"]

    if not controls_files:
        st.info("No controls found. Extract controls first (Tab 3).")
        return
    if not profile_files:
        st.info("No profiles found. Save a profile first (Tab 4).")
        return

    col1, col2 = st.columns([1, 1])

    with col1:
        blueprint_policy_name = st.text_input("Policy name", value="Data Management Policy", key="bp_policy_name")
        selected_controls = st.multiselect(
            "Select one or more controls JSON files",
            controls_files,
            default=[controls_files[0]],
            key="bp_controls_multi",
        )
        selected_profile = st.selectbox("Select business profile", profile_files, key="bp_profile_select")

        drafting_instructions = st.text_area(
            "Drafting instructions",
            value="Use a formal policy structure. Keep it business-specific and align responsibilities to the operating model.",
            key="bp_instructions",
            height=140,
        )

    with col2:
        st.markdown("### Optional reference policy")
        reference_choice = st.selectbox(
            "Choose existing reference policy",
            ["(none)"] + reference_files,
            key="bp_ref_select",
        )

        sample_policy_text = ""
        if reference_choice != "(none)":
            sample_policy_text = load_reference_policy_text(reference_choice)

        sample_policy_text = st.text_area(
            "Reference policy text / expected output style (editable)",
            value=sample_policy_text,
            key="bp_sample_policy_text",
            height=280,
        )

        new_ref_name = st.text_input("Save this reference text as (optional name)", value="", key="bp_new_ref_name")
        if st.button("Save reference policy text", key="bp_save_ref_btn"):
            if new_ref_name.strip() and sample_policy_text.strip():
                saved_ref = save_reference_policy_text(new_ref_name.strip(), sample_policy_text.strip())
                st.success(f"Saved reference: {saved_ref}")
            else:
                st.warning("Enter a reference name and text first.")

    if st.button("Save Blueprint", key="bp_save_btn"):
        try:
            result = create_policy_blueprint(
                policy_name=blueprint_policy_name,
                selected_control_files=selected_controls,
                selected_profile_file=selected_profile,
                sample_policy_text=sample_policy_text,
                drafting_instructions=drafting_instructions,
            )
            st.success(f"Blueprint saved: {result['out_path']}")
            st.json(result["blueprint"])

        except Exception as exc:
            st.exception(exc)

    st.divider()
    st.subheader("Existing blueprints")
    existing_blueprints = list_available_blueprints()
    if existing_blueprints:
        st.write(existing_blueprints)
    else:
        st.caption("No blueprints saved yet.")
