"""Streamlit page for reviewing and editing control taxonomy and overrides."""

from __future__ import annotations

import streamlit as st

from orchestrators.classification_admin_workflow import (
    build_override_rows,
    delete_override_for_control,
    get_classification_admin_page_data,
    load_override_entry_for_control,
    reset_taxonomy_to_default,
    save_override_from_form,
    save_taxonomy_from_text,
)


def _selectbox_index(options: list[str], value: str) -> int:
    """Return a safe selectbox index for the provided value."""

    return options.index(value) if value in options else 0


def _rerun_app() -> None:
    """Rerun the Streamlit script across Streamlit versions."""

    rerun = getattr(st, "rerun", None) or getattr(st, "experimental_rerun", None)
    if rerun:
        rerun()


def _resolve_override_form_defaults(selected_control: dict, existing_override: dict) -> dict:
    """Pick sensible defaults from override values first, then master control data."""

    override_payload = existing_override.get("overrides", {}) if isinstance(existing_override, dict) else {}
    metadata = existing_override.get("metadata", {}) if isinstance(existing_override, dict) else {}

    return {
        "category": override_payload.get("category", selected_control.get("category", "")),
        "control_type": override_payload.get("control_type", selected_control.get("control_type", "")),
        "severity": override_payload.get("severity", selected_control.get("severity", "")),
        "policy_tags": "; ".join(override_payload.get("policy_tags", selected_control.get("policy_tags", [])))
        if isinstance(override_payload.get("policy_tags", selected_control.get("policy_tags", [])), list)
        else str(override_payload.get("policy_tags", selected_control.get("policy_tags", ""))),
        "implementation_hint": override_payload.get("implementation_hint", selected_control.get("implementation_hint", "")),
        "note": metadata.get("note", ""),
        "updated_by": metadata.get("updated_by", ""),
        "source": metadata.get("source", "user_feedback") or "user_feedback",
    }


def render_classification_admin_page() -> None:
    """Render taxonomy and override administration tools."""

    st.write("Review and edit the external control taxonomy and statement-level user corrections.")

    page_data = get_classification_admin_page_data()
    taxonomy = page_data["taxonomy"]
    summary = page_data["summary"]

    c1, c2, c3 = st.columns(3)
    c1.metric("Topic rules", summary["topic_rule_count"])
    c2.metric("Saved overrides", summary["override_count"])
    c3.metric("Master controls", summary["master_control_count"])

    st.caption(f"Taxonomy file: `{page_data['taxonomy_path']}`")
    st.caption(f"Overrides file: `{page_data['overrides_path']}`")

    taxonomy_tab, overrides_tab = st.tabs(["Taxonomy", "Overrides"])

    with taxonomy_tab:
        st.subheader("Current Taxonomy")

        overview_left, overview_right = st.columns([1, 1])

        with overview_left:
            st.write("**Modality priority**")
            st.write(", ".join(taxonomy.get("modality", {}).get("priority", [])) or "Not configured")
            st.write("**Topic default**")
            st.write(taxonomy.get("topic", {}).get("default", "General"))

            st.write("**Topic rules**")
            topic_rows = []
            for rule in taxonomy.get("topic", {}).get("rules", []):
                topic_rows.append(
                    {
                        "label": rule.get("label", ""),
                        "keywords": ", ".join(rule.get("keywords", [])),
                    }
                )
            if topic_rows:
                st.dataframe(topic_rows, use_container_width=True)
            else:
                st.info("No topic rules configured.")

        with overview_right:
            fields = taxonomy.get("fields", {})
            for field_name in ["category", "control_type", "severity"]:
                field_config = fields.get(field_name, {})
                st.write(f"**{field_name}**")
                st.write(", ".join(field_config.get("allowed", [])) or "No allowed values configured")
                aliases = field_config.get("aliases", {})
                if aliases:
                    alias_rows = [{"alias": key, "maps_to": value} for key, value in aliases.items()]
                    st.dataframe(alias_rows, use_container_width=True)
                else:
                    st.caption("No aliases configured.")

        st.divider()
        st.subheader("Edit Taxonomy JSON")
        st.caption("You can change labels, keyword rules, aliases, and allowed values here.")

        taxonomy_editor_key = "classification_admin_taxonomy_editor"
        if taxonomy_editor_key not in st.session_state:
            st.session_state[taxonomy_editor_key] = page_data["taxonomy_json"]

        edited_taxonomy = st.text_area(
            "Taxonomy JSON",
            key=taxonomy_editor_key,
            height=560,
        )

        save_col, reset_col = st.columns([1, 1])
        with save_col:
            if st.button("Save taxonomy", key="classification_admin_save_taxonomy_btn", use_container_width=True):
                try:
                    result = save_taxonomy_from_text(edited_taxonomy)
                    st.session_state[taxonomy_editor_key] = result["taxonomy_json"]
                    st.success(f"Saved taxonomy to {result['path']}")
                    _rerun_app()
                except Exception as exc:
                    st.error(f"Failed to save taxonomy: {type(exc).__name__}: {exc}")

        with reset_col:
            if st.button("Reset taxonomy to defaults", key="classification_admin_reset_taxonomy_btn", use_container_width=True):
                try:
                    result = reset_taxonomy_to_default()
                    st.session_state[taxonomy_editor_key] = result["taxonomy_json"]
                    st.success("Taxonomy reset to built-in defaults.")
                    _rerun_app()
                except Exception as exc:
                    st.error(f"Failed to reset taxonomy: {type(exc).__name__}: {exc}")

    with overrides_tab:
        st.subheader("Saved Overrides")
        override_rows = build_override_rows(page_data["overrides"])
        if override_rows:
            st.dataframe(override_rows, use_container_width=True)
        else:
            st.info("No statement-level overrides saved yet.")

        st.divider()
        st.subheader("Create or Update Override")

        selectable_controls = page_data["selectable_controls"]
        source_mode = st.radio(
            "Override source",
            ["Existing control", "Custom statement"],
            horizontal=True,
            key="classification_admin_override_source_mode",
        )

        selected_control = {
            "label": "",
            "control_id": "",
            "statement": "",
            "category": "",
            "control_type": "",
            "severity": "",
            "policy_tags": [],
            "implementation_hint": "",
        }

        if source_mode == "Existing control" and selectable_controls:
            labels = [row["label"] for row in selectable_controls]
            selected_label = st.selectbox("Select a control", labels, key="classification_admin_existing_control_select")
            selected_control = next((row for row in selectable_controls if row["label"] == selected_label), selected_control)
        elif source_mode == "Existing control":
            st.info("No controls found in the master registry yet. Switch to custom statement to create an override.")

        if source_mode == "Custom statement":
            selected_control["statement"] = st.text_area(
                "Control statement",
                key="classification_admin_custom_statement",
                height=120,
            ).strip()

        control_text = str(selected_control.get("statement", "")).strip()
        existing_override = load_override_entry_for_control(control_text) if control_text else {}
        defaults = _resolve_override_form_defaults(selected_control, existing_override)

        if control_text:
            st.write("**Selected statement**")
            st.write(control_text)

            if selected_control.get("control_id"):
                st.caption(f"Control ID: `{selected_control['control_id']}`")

            base_left, base_right = st.columns(2)
            with base_left:
                st.write("**Current extracted classification**")
                st.json(
                    {
                        "category": selected_control.get("category", ""),
                        "control_type": selected_control.get("control_type", ""),
                        "severity": selected_control.get("severity", ""),
                        "policy_tags": selected_control.get("policy_tags", []),
                        "implementation_hint": selected_control.get("implementation_hint", ""),
                    }
                )
            with base_right:
                st.write("**Current override**")
                if existing_override:
                    st.json(existing_override)
                else:
                    st.info("No override saved for this statement.")

        fields = taxonomy.get("fields", {})
        category_allowed = [""] + fields.get("category", {}).get("allowed", [])
        control_type_allowed = [""] + fields.get("control_type", {}).get("allowed", [])
        severity_allowed = [""] + fields.get("severity", {}).get("allowed", [])

        category_input_mode = st.radio(
            "Category input mode",
            ["Pick allowed value", "Free text"],
            horizontal=True,
            key="classification_admin_category_input_mode",
        )

        with st.form("classification_admin_override_form"):
            if category_input_mode == "Pick allowed value":
                category = st.selectbox(
                    "Category",
                    category_allowed,
                    index=_selectbox_index(category_allowed, defaults["category"]),
                )
            else:
                category = st.text_input("Category", value=defaults["category"])

            control_type = st.selectbox(
                "Control type",
                control_type_allowed,
                index=_selectbox_index(control_type_allowed, defaults["control_type"]),
            )
            severity = st.selectbox(
                "Severity",
                severity_allowed,
                index=_selectbox_index(severity_allowed, defaults["severity"]),
            )
            policy_tags_text = st.text_input("Policy tags", value=defaults["policy_tags"], help="Use ; or , to separate multiple tags.")
            implementation_hint = st.text_area("Implementation hint", value=defaults["implementation_hint"], height=120)
            source = st.text_input("Source", value=defaults["source"])
            updated_by = st.text_input("Updated by", value=defaults["updated_by"])
            note = st.text_area("Note", value=defaults["note"], height=100)

            submitted = st.form_submit_button("Save override", use_container_width=True)
            if submitted:
                if not control_text:
                    st.error("Select an existing control or enter a custom statement before saving an override.")
                else:
                    try:
                        save_override_from_form(
                            control_text=control_text,
                            category=category,
                            control_type=control_type,
                            severity=severity,
                            policy_tags_text=policy_tags_text,
                            implementation_hint=implementation_hint,
                            note=note,
                            updated_by=updated_by,
                            source=source or "user_feedback",
                        )
                        st.success("Override saved successfully.")
                        _rerun_app()
                    except Exception as exc:
                        st.error(f"Failed to save override: {type(exc).__name__}: {exc}")

        if control_text and existing_override:
            if st.button("Delete override", key="classification_admin_delete_override_btn", type="secondary"):
                result = delete_override_for_control(control_text)
                if result["deleted"]:
                    st.success("Override deleted.")
                    _rerun_app()
                else:
                    st.error("Override could not be deleted.")
