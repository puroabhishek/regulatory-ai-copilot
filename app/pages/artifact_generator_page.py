"""Streamlit page for generating blueprint-driven artifacts."""

from pathlib import Path

import streamlit as st

from orchestrators.policy_workflow import (
    generate_artifacts_from_blueprint,
    list_available_blueprints,
    list_generated_artifacts,
)


def render_artifact_generator_page() -> None:
    """Render the artifact-generation workflow."""
    st.header("Policy Implementation")
    st.caption("Keep the current implementation logic: use a saved blueprint to generate the implementation plan, audit register, traceability matrix, and company control inventory.")
    artifacts_dir = Path("data/artifacts")
    blueprint_files = list_available_blueprints()

    if not blueprint_files:
        st.info("No blueprints available yet. Create one in Policy Generator first.")
        return

    selected_blueprint = st.selectbox("Select blueprint", blueprint_files, key="gen_blueprint_select")
    st.caption("Generation model is resolved centrally by the backend configuration.")

    if st.button("Generate Artifacts from Blueprint", key="gen_from_blueprint_btn"):
        try:
            result = generate_artifacts_from_blueprint(selected_blueprint=selected_blueprint, model=None)
            blueprint = result["blueprint"]
            policy_name = result["policy_name"]
            merged_controls = result["merged_controls"]
            company_control_rows = result["company_control_rows"]
            policy_md = result["policy_md"]
            plan_rows = result["plan_rows"]
            audit_rows = result["audit_rows"]
            trace_rows = result["trace_rows"]
            policy_path = result["policy_path"]
            plan_path = result["plan_path"]
            audit_path = result["audit_path"]
            trace_path = result["trace_path"]
            run_path = result["run_path"]

            st.success("Artifact generation completed successfully")

            st.markdown("## Generated Files")
            st.write("All files have been saved in:")
            st.code("data/artifacts/")

            generated_files = [
                {"artifact": "Policy Document", "file": policy_path},
                {"artifact": "Implementation Plan", "file": plan_path},
                {"artifact": "Audit Register", "file": audit_path},
                {"artifact": "Traceability Matrix", "file": trace_path},
                {"artifact": "Generation Run Record", "file": run_path},
            ]

            st.dataframe(generated_files, use_container_width=True)

            st.markdown("## What was generated")
            st.write(
                f"""
- **Policy name:** {policy_name}
- **Number of merged controls used:** {len(merged_controls)}
- **Business profile applied:** {blueprint.get('selected_profile_file', '')}
- **Controls sources used:** {", ".join(blueprint.get('selected_control_files', []))}
"""
            )

            st.markdown("## Artifact Previews")

            with st.expander("Preview: Policy Document", expanded=True):
                st.text(policy_md[:3000])

            with st.expander("Preview: Implementation Plan"):
                st.dataframe(plan_rows[:10], use_container_width=True)

            with st.expander("Preview: Audit Register"):
                st.dataframe(audit_rows[:10], use_container_width=True)

            with st.expander("Preview: Traceability Matrix"):
                st.dataframe(trace_rows[:10], use_container_width=True)

            st.markdown("## Company Control Inventory")
            st.dataframe(company_control_rows[:10], use_container_width=True)
            st.caption("Saved to: data/control_registry/company_controls.json and data/control_registry/company_controls.csv")

            st.markdown("## Download Artifacts")

            with open(policy_path, "rb") as handle:
                st.download_button(
                    label="Download Policy Document (.md)",
                    data=handle,
                    file_name=Path(policy_path).name,
                    mime="text/markdown",
                    key="dl_policy_md",
                )

            with open(plan_path, "rb") as handle:
                st.download_button(
                    label="Download Implementation Plan (.csv)",
                    data=handle,
                    file_name=Path(plan_path).name,
                    mime="text/csv",
                    key="dl_plan_csv",
                )

            with open(audit_path, "rb") as handle:
                st.download_button(
                    label="Download Audit Register (.csv)",
                    data=handle,
                    file_name=Path(audit_path).name,
                    mime="text/csv",
                    key="dl_audit_csv",
                )

            with open(trace_path, "rb") as handle:
                st.download_button(
                    label="Download Traceability Matrix (.csv)",
                    data=handle,
                    file_name=Path(trace_path).name,
                    mime="text/csv",
                    key="dl_trace_csv",
                )

        except Exception as exc:
            st.exception(exc)

    st.divider()
    st.subheader("Previously generated artifacts")

    existing_artifacts = list_generated_artifacts(str(artifacts_dir))
    if existing_artifacts:
        artifact_rows = []
        for file_name in existing_artifacts:
            artifact_rows.append(
                {
                    "file_name": file_name,
                    "stored_in": "data/artifacts/",
                }
            )
        st.dataframe(artifact_rows, use_container_width=True)
    else:
        st.caption("No artifacts generated yet.")
