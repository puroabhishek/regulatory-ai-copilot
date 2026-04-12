"""Streamlit page for creating business profiles with regulation suggestions."""

from pathlib import Path

import streamlit as st

from core.profiler import BusinessProfile, list_profiles, load_profile, save_profile
from domain.regulations.catalog import list_regulation_catalog, recommend_regulations_for_profile


def _save_current_recommendations(recommended_titles: list[str]) -> None:
    st.session_state["prof_applicable_regulations"] = recommended_titles


def render_business_profile_page() -> None:
    """Render the business-profile workflow and profile-linked regulation suggestions."""
    st.header("Business Profile")
    st.caption("Start here. Save the business context first so the product can suggest the regulations and guidelines that are likely to apply.")

    profile_dir = Path("data/profiles")
    catalog = list_regulation_catalog()
    catalog_titles = [entry["title"] for entry in catalog]

    left, right = st.columns([1.25, 1])

    with left:
        st.markdown("### Business context")
        profile_name = st.text_input("Profile name", value="my_fintech_qatar", key="prof_name")
        country = st.text_input("Country", value="Qatar", key="prof_country")
        regulator = st.text_input("Primary regulator", value="QCB", key="prof_regulator")

        sector = st.selectbox("Sector", ["Fintech", "Telecom", "Healthcare", "Government", "Other"], 0, key="prof_sector")
        business_type = st.selectbox(
            "Business type",
            ["Lending", "Insurance", "Payments", "Tech Service Provider", "SaaS", "Other"],
            0,
            key="prof_business_type",
        )
        business_model = st.selectbox("Business model", ["B2B", "B2C", "B2B2C", "Other"], 0, key="prof_business_model")

        target_customers = st.text_input("Target customers", value="SMEs", key="prof_target_customers")
        other_users = st.text_area(
            "Other users",
            value="Ops, Compliance, Finance, FI partners, Auditors",
            key="prof_other_users",
        )
        key_stakeholders = st.text_area(
            "Key stakeholders",
            value="QCB, Partner banks/FIs, Board, Compliance, IT/SecOps, Vendors",
            key="prof_stakeholders",
        )

        performs_kyc = "Not applicable"
        mandated_kyc = "Not applicable"
        lending_model = "Not applicable"
        lending_partners = ""

        if business_type == "Lending":
            performs_kyc = st.selectbox("Do you perform KYC?", ["Yes", "No", "Partner does it", "Not sure"], 0, key="prof_performs_kyc")
            mandated_kyc = st.selectbox("Are you mandated to perform KYC?", ["Yes", "No", "Not sure"], 0, key="prof_mandated_kyc")
            lending_model = st.selectbox("Do you lend from your own books?", ["Own books", "Partner-led", "Mixed"], 1, key="prof_lending_model")
            lending_partners = st.text_area("Lending partners", value="", key="prof_lending_partners")

        st.markdown("### Technology and data")
        cloud_use = st.selectbox("Do you use cloud?", ["Yes", "No", "Considering"], 0, key="prof_cloud_use")
        cloud_service_model = st.selectbox("Cloud service model", ["IaaS", "PaaS", "SaaS", "Mixed"], 2, key="prof_cloud_model")
        cloud_providers = st.multiselect("Cloud providers", ["AWS", "Azure", "GCP", "Oracle", "Other"], default=["AWS"], key="prof_cloud_providers")
        hosting_region = st.text_input("Hosting region", value="Qatar", key="prof_hosting_region")
        data_residency_required = st.selectbox("Data residency required?", ["Yes", "No", "Unsure"], 0, key="prof_residency")
        handles_pii = st.selectbox("Handles personal data?", ["Yes", "No"], 0, key="prof_pii")
        handles_financial_data = st.selectbox("Handles financial data?", ["Yes", "No"], 0, key="prof_fin")

    profile_snapshot = {
        "profile_name": profile_name,
        "country": country,
        "regulator": regulator,
        "sector": sector,
        "business_type": business_type,
        "business_model": business_model,
        "target_customers": target_customers,
        "other_users": other_users,
        "key_stakeholders": key_stakeholders,
        "performs_kyc": performs_kyc,
        "mandated_kyc": mandated_kyc,
        "lending_model": lending_model,
        "lending_partners": lending_partners,
        "cloud_use": cloud_use,
        "cloud_service_model": cloud_service_model,
        "cloud_providers": cloud_providers,
        "hosting_region": hosting_region,
        "data_residency_required": data_residency_required,
        "handles_pii": handles_pii,
        "handles_financial_data": handles_financial_data,
    }
    recommendations = recommend_regulations_for_profile(profile_snapshot)
    recommended_titles = [item["title"] for item in recommendations]

    if "prof_applicable_regulations" not in st.session_state:
        st.session_state["prof_applicable_regulations"] = recommended_titles

    with right:
        st.markdown("### Suggested regulations and guidelines")
        st.caption("Suggestions are based on the profile's regulator, business type, cloud usage, KYC footprint, and data handling.")

        if recommendations:
            recommendation_rows = []
            for item in recommendations:
                recommendation_rows.append(
                    {
                        "Regulation / Guideline": item["title"],
                        "Type": item.get("kind", ""),
                        "Why suggested": " ".join(item.get("reasons", [])),
                        "Ready in system": "Yes" if item.get("control_file_available") else "Upload needed",
                    }
                )
            st.dataframe(recommendation_rows, use_container_width=True, hide_index=True)
        else:
            st.info("No direct catalog match yet. You can still save the profile and later upload regulations manually.")

        st.button(
            "Use suggested regulations",
            key="prof_use_suggested_regs",
            use_container_width=True,
            on_click=_save_current_recommendations,
            args=(recommended_titles,),
        )

        st.multiselect(
            "Applicable regulations to store with this profile",
            options=catalog_titles,
            key="prof_applicable_regulations",
            help="This saved list becomes the default starting point for policy generation and gap analysis.",
        )

        if st.button("Save profile", key="save_profile_btn", type="primary", use_container_width=True):
            try:
                profile = BusinessProfile(
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
                    applicable_regulations=st.session_state.get("prof_applicable_regulations", []),
                    recommended_regulations=recommended_titles,
                )

                out_path = str(profile_dir / f"{profile_name}.json")
                save_profile(profile, out_path)
                st.success(f"Saved profile: {out_path}")
            except Exception as exc:
                st.exception(exc)

        st.divider()
        st.markdown("### Profile preview")
        preview_profile = {
            **profile_snapshot,
            "applicable_regulations": st.session_state.get("prof_applicable_regulations", []),
            "recommended_regulations": recommended_titles,
        }
        st.json(preview_profile)

        st.divider()
        st.markdown("### Saved profiles")
        profiles = list_profiles(str(profile_dir))
        if not profiles:
            st.info("No profiles saved yet.")
        else:
            selected = st.selectbox("Select profile to preview", profiles, key="prof_pick")
            data = load_profile(str(profile_dir / selected))
            st.json(data)
