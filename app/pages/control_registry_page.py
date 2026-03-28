"""Streamlit page for browsing and updating control registry data."""

import streamlit as st

from orchestrators.control_workflow import get_control_registry_page_data, update_company_control_record


def render_control_registry_page() -> None:
    """Render the control registry and company inventory cockpit."""
    st.write("View the global control master and manage company-specific control inventory.")

    page_data = get_control_registry_page_data()
    summary = page_data["summary"]

    st.subheader("Compliance Summary")
    c1, c2, c3 = st.columns(3)
    c1.metric("Total Controls", summary["total_controls"])
    c2.metric("Implemented", summary["status_breakdown"].get("Implemented", 0))
    c3.metric("High Risk Open", summary["high_risk_open"])

    st.write("### Status Breakdown")
    st.json(summary["status_breakdown"])

    st.divider()

    st.subheader("Global Controls Master")
    master_rows = page_data["master_rows"]
    if master_rows:
        st.dataframe(master_rows[:50], use_container_width=True)
        st.caption(f"Total controls in master registry: {len(master_rows)}")
    else:
        st.info("No controls in master registry yet. Extract controls first.")

    st.divider()

    st.subheader("Company Control Inventory")
    company_rows = page_data["company_rows"]

    if not company_rows:
        st.info("No company control inventory yet. Generate artifacts from a blueprint first.")
        return

    control_ids = [row.get("control_id", "") for row in company_rows if row.get("control_id", "")]
    selected_control_id = st.selectbox("Select control to update", control_ids, key="cockpit_control_select")

    selected_row = next((row for row in company_rows if row.get("control_id") == selected_control_id), None)

    if selected_row:
        st.write("### Selected Control")
        st.json(selected_row)

        col1, col2 = st.columns(2)

        with col1:
            allowed_statuses = ["Not Assessed", "In Progress", "Implemented", "Not Applicable"]
            current_status = selected_row.get("status", "Not Assessed")
            new_status = st.selectbox(
                "Status",
                allowed_statuses,
                index=allowed_statuses.index(current_status) if current_status in allowed_statuses else 0,
                key="cockpit_status",
            )

            new_owner = st.text_input(
                "Owner",
                value=selected_row.get("owner", ""),
                key="cockpit_owner",
            )

            new_evidence_link = st.text_input(
                "Evidence link / file reference",
                value=selected_row.get("evidence_link", ""),
                key="cockpit_evidence",
            )

        with col2:
            new_last_review = st.text_input(
                "Last review date (YYYY-MM-DD)",
                value=selected_row.get("last_review_date", ""),
                key="cockpit_last_review",
            )

            new_next_review = st.text_input(
                "Next review date (YYYY-MM-DD)",
                value=selected_row.get("next_review_date", ""),
                key="cockpit_next_review",
            )

            allowed_applicability = ["Applicable", "Needs Review", "Not Applicable"]
            current_applicability = selected_row.get("applicability", "Applicable")
            new_applicability = st.selectbox(
                "Applicability",
                allowed_applicability,
                index=allowed_applicability.index(current_applicability)
                if current_applicability in allowed_applicability
                else 0,
                key="cockpit_applicability",
            )

        if st.button("Update Control", key="cockpit_update_btn"):
            update_result = update_company_control_record(
                control_id=selected_control_id,
                updates={
                    "status": new_status,
                    "owner": new_owner,
                    "evidence_link": new_evidence_link,
                    "last_review_date": new_last_review,
                    "next_review_date": new_next_review,
                    "applicability": new_applicability,
                },
            )
            if update_result["updated"]:
                st.success("Control updated successfully.")
            else:
                st.error("Control update failed.")

    st.write("### Current Company Control Inventory")
    st.dataframe(company_rows[:100], use_container_width=True)
    st.caption(f"Total company controls: {len(company_rows)}")
