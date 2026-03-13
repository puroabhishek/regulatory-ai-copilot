import os
import tempfile
import time
from pathlib import Path

import streamlit as st

try:
    from core.control_registry import (
    register_controls_to_master,
    map_controls_to_company,
    load_controls_master,
    load_company_controls,
    update_company_control,
    get_company_control_summary,
    )
    from core.ingest import pdf_to_pages, save_pages
    from core.chunk import load_pages_jsonl, pages_to_chunks
    from core.index import index_chunks, query_index
    from core.postprocess import extract_requirements

    from core.profiler import BusinessProfile, save_profile, list_profiles, load_profile
    from core.controls import extract_controls_from_pages, save_controls_json, save_controls_csv

    from core.blueprint import (
        build_blueprint,
        save_blueprint,
        load_blueprint,
        list_blueprints,
        save_reference_policy,
        list_reference_policies,
        load_reference_policy,
    )

except Exception as e:
    st.set_page_config(page_title="Regulatory AI Copilot", layout="wide")
    st.title("🚨 App crashed during import")
    st.exception(e)
    st.stop()

st.set_page_config(page_title="Regulatory AI Copilot", layout="wide")
st.title("📘 Regulatory AI Copilot")

Path("data/processed").mkdir(parents=True, exist_ok=True)
Path("data/profiles").mkdir(parents=True, exist_ok=True)
Path("data/controls").mkdir(parents=True, exist_ok=True)
Path("data/artifacts").mkdir(parents=True, exist_ok=True)
Path("data/references").mkdir(parents=True, exist_ok=True)
Path("data/blueprints").mkdir(parents=True, exist_ok=True)
Path("data/generation_runs").mkdir(parents=True, exist_ok=True)
Path("data/control_registry").mkdir(parents=True, exist_ok=True)

tab1, tab2, tab3, tab4, tab5, tab6, tab7 = st.tabs(
    [
        "1) Upload & Save",
        "2) Index & Search",
        "3) Controls",
        "4) Business Profile",
        "5) Policy Blueprint",
        "6) Artifact Generator",
        "7) Control Registry",
    ]
)

# ----------------------------
# TAB 1: Upload & Save
# ----------------------------
with tab1:
    st.write("Upload a **text-based PDF** → extract text → save as JSONL for indexing.")
    uploaded = st.file_uploader("Upload a PDF", type=["pdf"], key="upload_pdf")

    if uploaded:
        with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp:
            tmp.write(uploaded.read())
            tmp_path = tmp.name

        doc_title = uploaded.name
        doc_id = Path(uploaded.name).stem.lower().replace(" ", "_")

        with st.spinner("Extracting text from PDF..."):
            pages = pdf_to_pages(tmp_path)

        os.unlink(tmp_path)

        total_chars = sum(len(p.get("text", "") or "") for p in pages)
        if total_chars < 200:
            st.error("This looks like a scanned PDF. Use a text-based PDF for now.")
        else:
            st.success("Text extracted successfully.")

        st.write(f"Pages extracted: **{len(pages)}** | Total characters: **{total_chars}**")

        st.subheader("Preview (first 2 pages)")
        for p in pages[:2]:
            st.markdown(f"### Page {p['page']}")
            st.text(p["text"][:2000] if p.get("text") else "[No text extracted]")

        out_file = f"data/processed/{doc_id}_pages.jsonl"
        if st.button("Save extracted text", key="save_extracted"):
            saved_path = save_pages(pages=pages, out_path=out_file, doc_id=doc_id, doc_title=doc_title)
            st.success(f"Saved: {saved_path}")

# ----------------------------
# TAB 2: Index & Search
# ----------------------------
with tab2:
    st.write("Index saved JSONL files → search semantically (RAG foundation).")

    processed_dir = Path("data/processed")
    files = sorted([f.name for f in processed_dir.glob("*_pages.jsonl")])

    if not files:
        st.info("No processed files yet. Go to Tab 1 and save a PDF first.")
    else:
        selected = st.selectbox("Select a processed JSONL file", files, key="index_select")
        chunk_tokens = st.slider("Chunk size (tokens)", 300, 1500, 900, 100, key="chunk_tokens")
        overlap_tokens = st.slider("Overlap (tokens)", 0, 400, 200, 50, key="overlap_tokens")
        top_k = st.slider("Top-K results", 3, 20, 8, 1, key="top_k")

        if st.button("Build / Update Index", key="build_index"):
            try:
                pages = load_pages_jsonl(str(processed_dir / selected))
                with st.spinner("Chunking pages..."):
                    chunks = pages_to_chunks(
                        pages=pages,
                        chunk_tokens=chunk_tokens,
                        overlap_tokens=overlap_tokens,
                    )
                with st.spinner("Indexing chunks (vector DB)..."):
                    added, skipped = index_chunks(chunks)

                st.success(f"Index updated. Added: {added}, Skipped: {skipped}")
            except Exception as e:
                st.exception(e)

        st.divider()
        st.subheader("Search")
        q = st.text_input("Your question", value="", key="search_q")

        if st.button("Search", key="search_btn"):
            try:
                if not q.strip():
                    st.warning("Please enter a question.")
                else:
                    res = query_index(q.strip(), top_k=top_k)

                    ids = res["ids"][0]
                    docs = res["documents"][0]
                    metas = res["metadatas"][0]
                    dists = res["distances"][0]

                    retrieved = []
                    for i in range(len(ids)):
                        retrieved.append(
                            {
                                "chunk_id": ids[i],
                                "text": docs[i],
                                "meta": metas[i],
                                "distance": dists[i],
                            }
                        )

                    st.subheader("Answer (Checklist)")
                    reqs = extract_requirements(retrieved, max_items=20)

                    if not reqs:
                        st.info("No requirement-like lines found. Try another question.")
                    else:
                        for j, item in enumerate(reqs, start=1):
                            st.write(f"{j}. {item}")

            except Exception as e:
                st.exception(e)

# ----------------------------
# TAB 3: Controls
# ----------------------------
with tab3:
    st.write("Extract **Controls** from processed PDFs → save as JSON/CSV.")
    st.caption("First run may be slower because local LLM classification is applied to controls.")

    processed_dir = Path("data/processed")
    files = sorted([f.name for f in processed_dir.glob("*_pages.jsonl")])

    if not files:
        st.info("No processed files yet. Go to Tab 1 and save a PDF first.")
    else:
        selected = st.selectbox("Select a processed JSONL file", files, key="controls_select")
        prefix = st.text_input("Control ID prefix", value="QCB-CCR", key="controls_prefix")
        min_len = st.slider("Minimum sentence length", 30, 200, 60, 10, key="controls_minlen")
        max_len = st.slider("Maximum sentence length", 200, 1500, 500, 50, key="controls_maxlen")

        if st.button("Extract Controls", key="extract_controls_btn"):
            try:
                start_time = time.time()

                with st.spinner("Extracting and classifying controls..."):
                    pages = load_pages_jsonl(str(processed_dir / selected))

                    doc_id = pages[0].get("doc_id", Path(selected).stem.replace("_pages", ""))
                    doc_title = pages[0].get("doc_title", selected)

                    controls = extract_controls_from_pages(
                        pages=pages,
                        doc_id=doc_id,
                        doc_title=doc_title,
                        prefix=prefix,
                        min_len=min_len,
                        max_len=max_len,
                    )

                    out_json = f"data/controls/{doc_id}_controls.json"
                    out_csv = f"data/controls/{doc_id}_controls.csv"

                    save_controls_json(controls, out_json)
                    save_controls_csv(controls, out_csv)
                    added_to_master = register_controls_to_master(controls)

                elapsed = round(time.time() - start_time, 2)

                st.success(f"✅ Controls extracted successfully: {len(controls)} controls")
                st.info(f"📚 Added to controls master registry: {added_to_master}")
                st.info(f"⏱ Time taken: {elapsed} seconds")
                st.code(out_json)
                st.code(out_csv)

                if controls:
                    preview_rows = []
                    for c in controls[:10]:
                        preview_rows.append(
                            {
                                "control_id": c.get("control_id", ""),
                                "statement": c.get("statement", ""),
                                "category": c.get("category", ""),
                                "severity": c.get("severity", ""),
                                "policy_tags": ", ".join(c.get("policy_tags", []))
                                if isinstance(c.get("policy_tags"), list)
                                else c.get("policy_tags", ""),
                            }
                        )
                    st.dataframe(preview_rows, use_container_width=True)
                else:
                    st.warning("No controls were extracted from this document.")

            except Exception as e:
                st.exception(e)

        st.divider()
        st.subheader("Available extracted control files")
        control_files = sorted([f.name for f in Path("data/controls").glob("*_controls.json")])
        if control_files:
            st.write(control_files)
        else:
            st.caption("No controls files available yet.")

# ----------------------------
# TAB 4: Business Profile
# ----------------------------
with tab4:
    st.write("Create a **Business Profile** → saved as JSON for later drafting.")

    profile_dir = Path("data/profiles")
    left, right = st.columns([1, 1])

    with left:
        profile_name = st.text_input("Profile name", value="my_fintech_qatar", key="prof_name")
        country = st.text_input("Country", value="Qatar", key="prof_country")
        regulator = st.text_input("Regulator", value="QCB", key="prof_regulator")

        sector = st.selectbox("Sector", ["Fintech", "Telecom", "Healthcare", "Government", "Other"], 0, key="prof_sector")
        business_type = st.selectbox("Business type", ["Lending", "Insurance", "Payments", "Tech Service Provider", "SaaS", "Other"], 0, key="prof_business_type")
        business_model = st.selectbox("Business model", ["B2B", "B2C", "B2B2C", "Other"], 0, key="prof_business_model")

        target_customers = st.text_input("Target customers", value="SMEs", key="prof_target_customers")
        other_users = st.text_area("Other users", value="Ops, Compliance, Finance, FI partners, Auditors", key="prof_other_users")
        key_stakeholders = st.text_area("Key stakeholders", value="QCB, Partner banks/FIs, Board, Compliance, IT/SecOps, Vendors", key="prof_stakeholders")

        performs_kyc = "Not applicable"
        mandated_kyc = "Not applicable"
        lending_model = "Not applicable"
        lending_partners = ""

        if business_type == "Lending":
            performs_kyc = st.selectbox("Do you perform KYC?", ["Yes", "No", "Partner does it", "Not sure"], 0, key="prof_performs_kyc")
            mandated_kyc = st.selectbox("Are you mandated to perform KYC?", ["Yes", "No", "Not sure"], 0, key="prof_mandated_kyc")
            lending_model = st.selectbox("Do you lend from your own books?", ["Own books", "Partner-led", "Mixed"], 1, key="prof_lending_model")
            lending_partners = st.text_area("Lending partners", value="", key="prof_lending_partners")

        cloud_use = st.selectbox("Do you use cloud?", ["Yes", "No", "Considering"], 0, key="prof_cloud_use")
        cloud_service_model = st.selectbox("Cloud service model", ["IaaS", "PaaS", "SaaS", "Mixed"], 2, key="prof_cloud_model")
        cloud_providers = st.multiselect("Cloud providers", ["AWS", "Azure", "GCP", "Oracle", "Other"], default=["AWS"], key="prof_cloud_providers")
        hosting_region = st.text_input("Hosting region", value="Qatar", key="prof_hosting_region")
        data_residency_required = st.selectbox("Data residency required?", ["Yes", "No", "Unsure"], 0, key="prof_residency")
        handles_pii = st.selectbox("Handles PII?", ["Yes", "No"], 0, key="prof_pii")
        handles_financial_data = st.selectbox("Handles financial data?", ["Yes", "No"], 0, key="prof_fin")

        if st.button("Save profile", key="save_profile_btn"):
            try:
                bp = BusinessProfile(
                    profile_name=profile_name,
                    country=country,
                    regulator=regulator,
                    sector=sector,
                    business_type=business_type,
                    business_model=business_model,
                    target_customers=target_customers,
                    other_users=other_users,
                    key_stakeholders=key_stakeholders,
                    performs_kyc=performs_kyc,
                    mandated_kyc=mandated_kyc,
                    lending_model=lending_model,
                    lending_partners=lending_partners,
                    cloud_use=cloud_use,
                    cloud_service_model=cloud_service_model,
                    cloud_providers=cloud_providers,
                    hosting_region=hosting_region,
                    data_residency_required=data_residency_required,
                    handles_pii=handles_pii,
                    handles_financial_data=handles_financial_data,
                )

                out_path = str(profile_dir / f"{profile_name}.json")
                save_profile(bp, out_path)
                st.success(f"Saved profile: {out_path}")

            except Exception as e:
                st.exception(e)

    with right:
        profs = list_profiles(str(profile_dir))
        if not profs:
            st.info("No profiles saved yet.")
        else:
            pick = st.selectbox("Select profile to preview", profs, key="prof_pick")
            data = load_profile(str(profile_dir / pick))
            st.json(data)

# ----------------------------
# TAB 5: Policy Blueprint
# ----------------------------
with tab5:
    st.write("Create a **Policy Blueprint** using selected controls, business profile, and optional sample policy text.")

    controls_dir = Path("data/controls")
    profiles_dir = Path("data/profiles")
    refs_dir = Path("data/references")
    blueprints_dir = Path("data/blueprints")

    controls_files = sorted([f.name for f in controls_dir.glob("*_controls.json")])
    profile_files = sorted([f.name for f in profiles_dir.glob("*.json")])
    reference_files = list_reference_policies(str(refs_dir))

    if not controls_files:
        st.info("No controls found. Extract controls first (Tab 3).")
    elif not profile_files:
        st.info("No profiles found. Save a profile first (Tab 4).")
    else:
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
                sample_policy_text = load_reference_policy(str(refs_dir / reference_choice))

            sample_policy_text = st.text_area(
                "Reference policy text / expected output style (editable)",
                value=sample_policy_text,
                key="bp_sample_policy_text",
                height=280,
            )

            new_ref_name = st.text_input("Save this reference text as (optional name)", value="", key="bp_new_ref_name")
            if st.button("Save reference policy text", key="bp_save_ref_btn"):
                if new_ref_name.strip() and sample_policy_text.strip():
                    saved_ref = save_reference_policy(new_ref_name.strip(), sample_policy_text.strip())
                    st.success(f"Saved reference: {saved_ref}")
                else:
                    st.warning("Enter a reference name and text first.")

        if st.button("Save Blueprint", key="bp_save_btn"):
            try:
                profile_data = load_profile(str(profiles_dir / selected_profile))

                blueprint = build_blueprint(
                    policy_name=blueprint_policy_name,
                    selected_control_files=selected_controls,
                    selected_profile_file=selected_profile,
                    profile_data=profile_data,
                    sample_policy_text=sample_policy_text,
                    drafting_instructions=drafting_instructions,
                )

                safe_name = blueprint_policy_name.strip().replace(" ", "_")
                out_path = str(blueprints_dir / f"{safe_name}_blueprint.json")
                save_blueprint(blueprint, out_path)

                st.success(f"Blueprint saved: {out_path}")
                st.json(blueprint)

            except Exception as e:
                st.exception(e)

        st.divider()
        st.subheader("Existing blueprints")
        existing_blueprints = list_blueprints(str(blueprints_dir))
        if existing_blueprints:
            st.write(existing_blueprints)
        else:
            st.caption("No blueprints saved yet.")

# ----------------------------
# TAB 6: Artifact Generator (blueprint-driven)
# ----------------------------
with tab6:
    st.write("Generate bespoke artifacts from a saved **Policy Blueprint**.")

    try:
        from core.generator import (
            load_json,
            normalize_policy_name,
            merge_controls,
            generate_policy_md_from_blueprint,
            build_project_plan_rows,
            build_audit_register_rows,
            build_traceability_rows,
            save_text,
            save_csv,
            save_generation_run,
        )
    except Exception as e:
        st.error("Generator module not available or has an error: core/generator.py")
        st.exception(e)
        st.stop()

    blueprints_dir = Path("data/blueprints")
    controls_dir = Path("data/controls")
    artifacts_dir = Path("data/artifacts")

    blueprint_files = list_blueprints(str(blueprints_dir))

    if not blueprint_files:
        st.info("No blueprints available. Create one in Tab 5 first.")
    else:
        selected_blueprint = st.selectbox("Select blueprint", blueprint_files, key="gen_blueprint_select")

        if st.button("Generate Artifacts from Blueprint", key="gen_from_blueprint_btn"):
            try:
                blueprint = load_blueprint(str(blueprints_dir / selected_blueprint))
                control_sets = []

                for f in blueprint["selected_control_files"]:
                    control_sets.append(load_json(str(controls_dir / f)))

                merged_controls = merge_controls(control_sets, blueprint["selected_control_files"])
                company_control_rows = map_controls_to_company(blueprint["profile_summary"], merged_controls)

                policy_name = blueprint["policy_name"]
                policy_slug = normalize_policy_name(policy_name)

                policy_md = generate_policy_md_from_blueprint(
                    blueprint=blueprint,
                    controls=merged_controls,
                    model="qwen2.5:1.5b",
                )

                plan_rows = build_project_plan_rows(policy_name, merged_controls, blueprint["profile_summary"])
                audit_rows = build_audit_register_rows(policy_name, merged_controls, blueprint["profile_summary"])
                trace_rows = build_traceability_rows(policy_name, merged_controls, blueprint["profile_summary"])

                policy_path = str(artifacts_dir / f"{policy_slug}.md")
                plan_path = str(artifacts_dir / f"{policy_slug}_implementation_plan.csv")
                audit_path = str(artifacts_dir / f"{policy_slug}_audit_register.csv")
                trace_path = str(artifacts_dir / f"{policy_slug}_traceability_matrix.csv")

                save_text(policy_path, policy_md)
                save_csv(plan_path, plan_rows)
                save_csv(audit_path, audit_rows)
                save_csv(trace_path, trace_rows)

                run_path = save_generation_run(policy_slug, blueprint, policy_md)

                st.success("✅ Artifact generation completed successfully")

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

                with open(policy_path, "rb") as f:
                    st.download_button(
                        label="Download Policy Document (.md)",
                        data=f,
                        file_name=Path(policy_path).name,
                        mime="text/markdown",
                        key="dl_policy_md",
                    )

                with open(plan_path, "rb") as f:
                    st.download_button(
                        label="Download Implementation Plan (.csv)",
                        data=f,
                        file_name=Path(plan_path).name,
                        mime="text/csv",
                        key="dl_plan_csv",
                    )

                with open(audit_path, "rb") as f:
                    st.download_button(
                        label="Download Audit Register (.csv)",
                        data=f,
                        file_name=Path(audit_path).name,
                        mime="text/csv",
                        key="dl_audit_csv",
                    )

                with open(trace_path, "rb") as f:
                    st.download_button(
                        label="Download Traceability Matrix (.csv)",
                        data=f,
                        file_name=Path(trace_path).name,
                        mime="text/csv",
                        key="dl_trace_csv",
                    )

            except Exception as e:
                st.exception(e)

        st.divider()
        st.subheader("Previously generated artifacts")

        existing_artifacts = sorted([f.name for f in artifacts_dir.glob("*") if f.is_file()])
        if existing_artifacts:
            artifact_rows = []
            for f in existing_artifacts:
                artifact_rows.append(
                    {
                        "file_name": f,
                        "stored_in": "data/artifacts/",
                    }
                )
            st.dataframe(artifact_rows, use_container_width=True)
        else:
            st.caption("No artifacts generated yet.")

# ----------------------------
# TAB 7: Control Registry / Compliance Cockpit
# ----------------------------
with tab7:
    st.write("View the global control master and manage company-specific control inventory.")

    summary = get_company_control_summary()

    st.subheader("Compliance Summary")
    c1, c2, c3 = st.columns(3)
    c1.metric("Total Controls", summary["total_controls"])
    c2.metric("Implemented", summary["status_breakdown"].get("Implemented", 0))
    c3.metric("High Risk Open", summary["high_risk_open"])

    st.write("### Status Breakdown")
    st.json(summary["status_breakdown"])

    st.divider()

    st.subheader("Global Controls Master")
    master_rows = load_controls_master()
    if master_rows:
        st.dataframe(master_rows[:50], use_container_width=True)
        st.caption(f"Total controls in master registry: {len(master_rows)}")
    else:
        st.info("No controls in master registry yet. Extract controls first.")

    st.divider()

    st.subheader("Company Control Inventory")
    company_rows = load_company_controls()

    if not company_rows:
        st.info("No company control inventory yet. Generate artifacts from a blueprint first.")
    else:
        control_ids = [r.get("control_id", "") for r in company_rows if r.get("control_id", "")]
        selected_control_id = st.selectbox("Select control to update", control_ids, key="cockpit_control_select")

        selected_row = next((r for r in company_rows if r.get("control_id") == selected_control_id), None)

        if selected_row:
            st.write("### Selected Control")
            st.json(selected_row)

            col1, col2 = st.columns(2)

            with col1:
                new_status = st.selectbox(
                    "Status",
                    ["Not Assessed", "In Progress", "Implemented", "Not Applicable"],
                    index=["Not Assessed", "In Progress", "Implemented", "Not Applicable"].index(
                        selected_row.get("status", "Not Assessed")
                    )
                    if selected_row.get("status", "Not Assessed") in ["Not Assessed", "In Progress", "Implemented", "Not Applicable"]
                    else 0,
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

                new_applicability = st.selectbox(
                    "Applicability",
                    ["Applicable", "Needs Review", "Not Applicable"],
                    index=["Applicable", "Needs Review", "Not Applicable"].index(
                        selected_row.get("applicability", "Applicable")
                    )
                    if selected_row.get("applicability", "Applicable") in ["Applicable", "Needs Review", "Not Applicable"]
                    else 0,
                    key="cockpit_applicability",
                )

            if st.button("Update Control", key="cockpit_update_btn"):
                ok = update_company_control(
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
                if ok:
                    st.success("Control updated successfully.")
                else:
                    st.error("Control update failed.")

        st.write("### Current Company Control Inventory")
        st.dataframe(company_rows[:100], use_container_width=True)
        st.caption(f"Total company controls: {len(company_rows)}")