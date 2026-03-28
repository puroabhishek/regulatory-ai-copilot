"""Streamlit page for creating and previewing business profiles."""

from pathlib import Path

import streamlit as st

from core.profiler import BusinessProfile, list_profiles, load_profile, save_profile


def render_business_profile_page() -> None:
    """Render the business-profile creation and preview workflow."""
    st.write("Create a **Business Profile** -> saved as JSON for later drafting.")

    profile_dir = Path("data/profiles")
    left, right = st.columns([1, 1])

    with left:
        profile_name = st.text_input("Profile name", value="my_fintech_qatar", key="prof_name")
        country = st.text_input("Country", value="Qatar", key="prof_country")
        regulator = st.text_input("Regulator", value="QCB", key="prof_regulator")

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

        cloud_use = st.selectbox("Do you use cloud?", ["Yes", "No", "Considering"], 0, key="prof_cloud_use")
        cloud_service_model = st.selectbox("Cloud service model", ["IaaS", "PaaS", "SaaS", "Mixed"], 2, key="prof_cloud_model")
        cloud_providers = st.multiselect("Cloud providers", ["AWS", "Azure", "GCP", "Oracle", "Other"], default=["AWS"], key="prof_cloud_providers")
        hosting_region = st.text_input("Hosting region", value="Qatar", key="prof_hosting_region")
        data_residency_required = st.selectbox("Data residency required?", ["Yes", "No", "Unsure"], 0, key="prof_residency")
        handles_pii = st.selectbox("Handles PII?", ["Yes", "No"], 0, key="prof_pii")
        handles_financial_data = st.selectbox("Handles financial data?", ["Yes", "No"], 0, key="prof_fin")

        if st.button("Save profile", key="save_profile_btn"):
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
                )

                out_path = str(profile_dir / f"{profile_name}.json")
                save_profile(profile, out_path)
                st.success(f"Saved profile: {out_path}")

            except Exception as exc:
                st.exception(exc)

    with right:
        profiles = list_profiles(str(profile_dir))
        if not profiles:
            st.info("No profiles saved yet.")
        else:
            selected = st.selectbox("Select profile to preview", profiles, key="prof_pick")
            data = load_profile(str(profile_dir / selected))
            st.json(data)
