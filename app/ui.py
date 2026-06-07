"""4-step guided journey UI for the Regulatory AI Copilot."""
import sys
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

import streamlit as st

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------
APP_TITLE = "Regulatory AI Copilot"

QATAR_REGULATIONS = [
    "QCB eKYC Regulation",
    "QCB Cloud Computing Regulation",
    "QCB IT Risk Management Regulation",
    "QCB Outsourcing Regulation",
    "AML/CFT Law (Law No. 20 of 2019)",
    "QCB General Licensing Regulations",
]

DATA_HANDLED_OPTIONS = [
    "Customer PII",
    "Financial Data",
    "Biometric Data",
    "Transaction Records",
]

DATA_DIRECTORIES = [
    "data/processed",
    "data/profiles",
    "data/controls",
    "data/artifacts",
    "data/references",
    "data/blueprints",
    "data/generation_runs",
    "data/control_registry",
    "data/gap_analysis",
]

STEP_LABELS = [
    "Step 1: Business Profile",
    "Step 2: Compliance Work",
    "Step 3: Policy Vault",
    "Step 4: Audit Report",
]


def _ensure_app_directories() -> None:
    for directory in DATA_DIRECTORIES:
        Path(directory).mkdir(parents=True, exist_ok=True)


# ---------------------------------------------------------------------------
# Step 1 — Business Profile
# ---------------------------------------------------------------------------

def _render_step1_business_profile() -> None:
    st.header("Business Profile")
    st.write("Tell us about your business so we can recommend the right regulations.")

    existing = st.session_state.get("profile", {})

    with st.form("business_profile_form"):
        country = st.text_input("Country", value=existing.get("country", "Qatar"))
        sector = st.text_input("Sector", value=existing.get("sector", ""))
        sub_sector = st.text_input("Sub-sector", value=existing.get("sub_sector", ""))
        activity = st.text_input("Business Activity", value=existing.get("activity", ""))
        business_model = st.text_input("Business Model", value=existing.get("business_model", ""))
        data_handled = st.multiselect(
            "Data Handled",
            options=DATA_HANDLED_OPTIONS,
            default=existing.get("data_handled", []),
        )
        uses_cloud = st.checkbox("Uses Cloud Services", value=existing.get("uses_cloud", False))
        has_lending = st.checkbox("Has Lending Activities", value=existing.get("has_lending", False))
        save_btn = st.form_submit_button("Save Profile")

    if save_btn:
        profile = {
            "country": country.strip(),
            "sector": sector.strip(),
            "sub_sector": sub_sector.strip(),
            "activity": activity.strip(),
            "business_model": business_model.strip(),
            "data_handled": data_handled,
            "uses_cloud": uses_cloud,
            "has_lending": has_lending,
        }
        st.session_state["profile"] = profile
        applicable_count = _estimate_applicable_regulations(profile)
        st.success(f"Profile saved. {applicable_count} regulations may apply based on your sector.")

    if st.session_state.get("profile"):
        p = st.session_state["profile"]
        st.subheader("Current Profile")
        col1, col2 = st.columns(2)
        with col1:
            st.write(f"**Country:** {p.get('country', '')}")
            st.write(f"**Sector:** {p.get('sector', '')}")
            st.write(f"**Sub-sector:** {p.get('sub_sector', '')}")
            st.write(f"**Activity:** {p.get('activity', '')}")
        with col2:
            st.write(f"**Business Model:** {p.get('business_model', '')}")
            st.write(f"**Data Handled:** {', '.join(p.get('data_handled', []))}")
            st.write(f"**Uses Cloud:** {'Yes' if p.get('uses_cloud') else 'No'}")
            st.write(f"**Has Lending:** {'Yes' if p.get('has_lending') else 'No'}")


def _estimate_applicable_regulations(profile: dict) -> int:
    count = 1  # Always at least QCB General
    if profile.get("uses_cloud"):
        count += 1
    if profile.get("has_lending"):
        count += 1
    data = profile.get("data_handled", [])
    if "Financial Data" in data or "Customer PII" in data:
        count += 1
    if "Biometric Data" in data:
        count += 1
    return min(count, len(QATAR_REGULATIONS))


# ---------------------------------------------------------------------------
# Step 2 — Compliance Work
# ---------------------------------------------------------------------------

def _render_step2_compliance_work() -> None:
    st.header("Compliance Work")

    if not st.session_state.get("profile"):
        st.info("Please complete Step 1 (Business Profile) first.")
        return

    tab_a, tab_b = st.tabs(["Create Policy", "Analyse Existing Policy"])

    with tab_a:
        _render_create_policy()

    with tab_b:
        _render_analyse_policy()


def _render_create_policy() -> None:
    st.subheader("Create a New Policy")

    policy_name = st.text_input("Policy Name", key="cp_policy_name")
    selected_regulations = st.multiselect(
        "Applicable Regulations",
        options=QATAR_REGULATIONS,
        key="cp_regulations",
    )
    drafting_instructions = st.text_area(
        "Drafting Instructions (optional)",
        key="cp_instructions",
        height=100,
    )
    style_ref_file = st.file_uploader(
        "Style Reference (optional .md or .txt)",
        type=["md", "txt"],
        key="cp_style_ref",
    )

    if st.button("Generate Policy", key="cp_generate"):
        if not policy_name.strip():
            st.error("Please enter a policy name.")
            return
        if not selected_regulations:
            st.error("Please select at least one regulation.")
            return
        _run_policy_generation(policy_name, selected_regulations, drafting_instructions, style_ref_file)

    if st.session_state.get("generated_policy_md"):
        _render_policy_output()


def _run_policy_generation(policy_name, selected_regulations, drafting_instructions, style_ref_file):
    from services.auth.session import get_current_org_id
    from services.storage.paths import artifacts_dir, profiles_dir, blueprints_dir, ensure_org_dirs

    org_id = get_current_org_id()
    org_slug = _get_org_slug(org_id)
    ensure_org_dirs(org_slug)

    sample_policy_text = ""
    if style_ref_file is not None:
        try:
            sample_policy_text = style_ref_file.read().decode("utf-8", errors="replace")
        except Exception as exc:
            st.warning(f"Could not read style reference file: {exc}")

    prof_dir = profiles_dir(org_slug)
    profile_files = list(prof_dir.glob("*.json")) if prof_dir.exists() else []
    if not profile_files:
        global_profiles = Path("data/profiles")
        profile_files = list(global_profiles.glob("*.json")) if global_profiles.exists() else []

    selected_profile_file = profile_files[0].name if profile_files else "default_profile.json"
    effective_profiles_dir = (
        str(prof_dir) if (profile_files and prof_dir.exists()) else "data/profiles"
    )

    try:
        with st.spinner("Generating policy... this may take a few minutes."):
            from orchestrators.policy_workflow import create_policy_from_scratch
            result = create_policy_from_scratch(
                policy_name=policy_name,
                policy_context="",
                selected_profile_file=selected_profile_file,
                selected_regulations=selected_regulations,
                sample_policy_text=sample_policy_text,
                drafting_instructions=drafting_instructions,
                profiles_dir=effective_profiles_dir,
                blueprints_dir=str(blueprints_dir(org_slug)),
                artifacts_dir=str(artifacts_dir(org_slug)),
                model=st.session_state.get("model_override"),
            )
        policy_md = result.get("policy_md", "")
        st.session_state["generated_policy_md"] = policy_md
        st.session_state["generated_policy_name"] = policy_name
        st.session_state["generated_policy_ref_id"] = result.get("policy_path", policy_name)
        st.success("Policy generated successfully!")

        try:
            _save_policy_to_db(policy_name, policy_md, selected_regulations, org_id)
        except Exception as db_exc:
            st.warning(f"Policy generated but could not save to database: {db_exc}")

    except Exception as exc:
        st.error(f"Policy generation failed: {type(exc).__name__}: {exc}")


def _save_policy_to_db(policy_name, policy_md, selected_regulations, org_id):
    from services.db.session import session_scope
    from models.policy import Policy
    from services.auth.session import get_current_user_id

    user_id = get_current_user_id()
    with session_scope() as db:
        pol = Policy(
            policy_name=policy_name,
            organization_id=org_id,
            owner_user_id=user_id,
            policy_text=policy_md,
            status="draft",
            source_context={"selected_regulations": selected_regulations},
        )
        db.add(pol)


def _render_policy_output() -> None:
    policy_md = st.session_state["generated_policy_md"]
    policy_name = st.session_state.get("generated_policy_name", "policy")
    ref_id = st.session_state.get("generated_policy_ref_id", "")

    st.subheader("Generated Policy")
    st.markdown(policy_md)

    st.write("**Was this policy useful?**")
    col1, col2, _ = st.columns([1, 1, 8])
    with col1:
        if st.button("👍", key="policy_thumbs_up"):
            _write_feedback("policy", ref_id, "positive")
            st.success("Thanks!")
    with col2:
        if st.button("👎", key="policy_thumbs_down"):
            _write_feedback("policy", ref_id, "negative")
            st.info("Thanks!")

    st.download_button(
        label="Download Policy (.md)",
        data=policy_md,
        file_name=f"{policy_name.replace(' ', '_')}.md",
        mime="text/markdown",
        key="policy_download",
    )


def _write_feedback(output_type: str, ref_id: str, rating: str, reason_code: str = "") -> None:
    try:
        from services.db.session import session_scope
        from models.feedback import OutputFeedback
        from services.auth.session import get_current_org_id, get_current_user_id

        org_id = get_current_org_id()
        user_id = get_current_user_id()
        with session_scope() as db:
            db.add(OutputFeedback(
                org_id=org_id,
                user_id=user_id,
                output_type=output_type,
                output_ref_id=str(ref_id)[:36],
                rating=rating,
                reason_code=reason_code or None,
            ))
    except Exception as exc:
        st.warning(f"Could not record feedback: {exc}")


def _render_analyse_policy() -> None:
    st.subheader("Analyse Existing Policy")

    policy_text = st.text_area("Paste your policy text here", height=200, key="ap_policy_text")
    uploaded_policy = st.file_uploader(
        "Or upload policy file (.txt, .md)",
        type=["txt", "md"],
        key="ap_policy_file",
    )

    controls_base = Path("data/controls")
    control_files = sorted(controls_base.glob("*.json")) if controls_base.exists() else []
    control_file_names = [f.name for f in control_files]

    if not control_file_names:
        st.warning("No control files found in data/controls/. Upload controls via the Admin portal.")
        return

    selected_controls_file = st.selectbox(
        "Select Control Set",
        options=control_file_names,
        key="ap_controls_file",
    )

    if st.button("Run Analysis", key="ap_run"):
        effective_policy_text = policy_text.strip()
        if uploaded_policy is not None:
            try:
                effective_policy_text = uploaded_policy.read().decode("utf-8", errors="replace")
            except Exception as exc:
                st.error(f"Could not read uploaded file: {exc}")
                return

        if not effective_policy_text:
            st.error("Please provide policy text or upload a policy file.")
            return

        _run_gap_analysis(effective_policy_text, selected_controls_file)

    if st.session_state.get("gap_analysis_results"):
        _render_gap_results()


def _load_controls_from_file(controls_file_name: str):
    import json
    controls_path = Path("data/controls") / controls_file_name
    if not controls_path.exists():
        return []
    data = json.loads(controls_path.read_text(encoding="utf-8"))
    if isinstance(data, list):
        return data
    if isinstance(data, dict) and "controls" in data:
        return data["controls"]
    return []


def _run_gap_analysis(policy_text: str, controls_file: str) -> None:
    from domain.gaps.policy_coverage import analyze_policy_coverage
    from schemas.control import Control

    controls_raw = _load_controls_from_file(controls_file)
    if not controls_raw:
        st.warning("No controls found in the selected file.")
        return

    results = []
    progress_bar = st.progress(0)
    status_text = st.empty()
    total = len(controls_raw)

    for i, ctrl_data in enumerate(controls_raw):
        try:
            control = Control(
                control_id=str(
                    ctrl_data.get("control_id") or ctrl_data.get("id") or f"CTRL-{i + 1}"
                ),
                statement=str(
                    ctrl_data.get("statement") or ctrl_data.get("control_statement") or ""
                ),
            )
            if not control.statement:
                continue
            status_text.text(f"Analysing {i + 1}/{total}: {control.control_id}")
            assessment = analyze_policy_coverage(
                control=control,
                policy_text=policy_text,
                model=st.session_state.get("model_override"),
            )
            results.append({
                "control_id": control.control_id,
                "statement": control.statement[:100] + ("..." if len(control.statement) > 100 else ""),
                "status": assessment.status,
                "reason": assessment.reason,
                "remediation": assessment.remediation,
            })
        except Exception as exc:
            results.append({
                "control_id": str(ctrl_data.get("control_id") or f"CTRL-{i + 1}"),
                "statement": str(
                    ctrl_data.get("statement") or ctrl_data.get("control_statement") or ""
                )[:100],
                "status": "Error",
                "reason": str(exc),
                "remediation": "",
            })
        progress_bar.progress((i + 1) / total)

    progress_bar.empty()
    status_text.empty()
    st.session_state["gap_analysis_results"] = results
    st.session_state["gap_analysis_policy_text"] = policy_text


def _render_gap_results() -> None:
    import pandas as pd

    results = st.session_state["gap_analysis_results"]
    if not results:
        st.info("No results to display.")
        return

    covered = sum(1 for r in results if r["status"] == "Covered")
    partial = sum(1 for r in results if r["status"] == "Partially Covered")
    missing = sum(1 for r in results if r["status"] == "Missing")
    total = len(results)
    score = (covered / total * 100) if total > 0 else 0

    st.subheader(f"Compliance Score: {score:.1f}%")
    col1, col2, col3 = st.columns(3)
    col1.metric("Covered", covered)
    col2.metric("Partially Covered", partial)
    col3.metric("Missing", missing)

    def color_status(val):
        colors = {
            "Covered": "background-color: #d4edda; color: #155724",
            "Partially Covered": "background-color: #fff3cd; color: #856404",
            "Missing": "background-color: #f8d7da; color: #721c24",
        }
        return colors.get(val, "")

    df = pd.DataFrame(results)
    if not df.empty and "status" in df.columns:
        try:
            styled = df.style.applymap(color_status, subset=["status"])
            st.dataframe(styled, use_container_width=True)
        except Exception:
            st.dataframe(df, use_container_width=True)
    else:
        st.dataframe(df, use_container_width=True)

    st.write("**Provide feedback on individual findings:**")
    for i, row in enumerate(results):
        col1, col2, col3 = st.columns([5, 1, 1])
        with col1:
            st.write(f"`{row['control_id']}` — {row['status']}")
        with col2:
            if st.button("👍", key=f"gap_up_{i}"):
                _write_feedback("gap_analysis", row["control_id"], "positive")
                st.success("Thanks!")
        with col3:
            if st.button("👎", key=f"gap_down_{i}"):
                _write_feedback("gap_analysis", row["control_id"], "negative")
                st.info("Thanks!")


# ---------------------------------------------------------------------------
# Step 3 — Policy Vault
# ---------------------------------------------------------------------------

def _render_step3_policy_vault() -> None:
    st.header("Policy Vault")

    from services.auth.session import get_current_org_id
    org_id = get_current_org_id()
    org_slug = _get_org_slug(org_id)

    policies_from_db = _load_policies_from_db(org_id)

    if policies_from_db:
        st.subheader(f"Policies ({len(policies_from_db)} found)")
        for pol in policies_from_db:
            created = getattr(pol, "created_at", None) or ""
            label = f"{pol.policy_name} — {str(created)[:10]}"
            with st.expander(label):
                if pol.policy_text:
                    preview = pol.policy_text
                    st.markdown(preview[:3000] + ("..." if len(preview) > 3000 else ""))
                    st.download_button(
                        label="Download",
                        data=pol.policy_text,
                        file_name=f"{pol.policy_name.replace(' ', '_')}.md",
                        mime="text/markdown",
                        key=f"dl_policy_{pol.id}",
                    )
                else:
                    st.info("No policy text stored.")
    else:
        st.info("No policies found in the database for this organization.")
        st.write("Showing recently generated files from artifacts directory as fallback:")
        _render_artifact_fallback(org_slug)


def _load_policies_from_db(org_id):
    try:
        from services.db.session import session_scope
        from models.policy import Policy

        with session_scope() as db:
            if org_id:
                policies = (
                    db.query(Policy)
                    .filter(Policy.organization_id == org_id)
                    .order_by(Policy.created_at.desc())
                    .all()
                )
            else:
                policies = (
                    db.query(Policy)
                    .order_by(Policy.created_at.desc())
                    .limit(50)
                    .all()
                )
            return list(policies)
    except Exception as exc:
        st.error(f"Could not load policies from database: {exc}")
        return []


def _render_artifact_fallback(org_slug) -> None:
    from services.storage.paths import artifacts_dir

    art_dir = artifacts_dir(org_slug)
    if art_dir.exists():
        files = sorted(art_dir.glob("*.md"))
    else:
        files = sorted(Path("data/artifacts").glob("*.md"))

    if not files:
        st.write("No artifact files found.")
        return

    for f in files:
        with st.expander(f.name):
            try:
                content = f.read_text(encoding="utf-8")
                st.markdown(content[:2000] + ("..." if len(content) > 2000 else ""))
                st.download_button(
                    label="Download",
                    data=content,
                    file_name=f.name,
                    mime="text/markdown",
                    key=f"dl_art_{f.name}",
                )
            except Exception as exc:
                st.error(f"Could not read file: {exc}")


# ---------------------------------------------------------------------------
# Step 4 — Audit Report
# ---------------------------------------------------------------------------

def _render_step4_audit_report() -> None:
    st.header("Audit Report")

    from services.auth.session import get_current_org_id
    org_id = get_current_org_id()

    policies = _load_policies_from_db(org_id)
    total_policies = len(policies)

    gap_results = st.session_state.get("gap_analysis_results", [])
    if gap_results:
        covered = sum(1 for r in gap_results if r["status"] == "Covered")
        total_controls = len(gap_results)
        avg_score = (covered / total_controls * 100) if total_controls > 0 else 0.0
        open_gaps = [r for r in gap_results if r["status"] == "Missing"]
    else:
        avg_score = 0.0
        open_gaps = []

    col1, col2, col3 = st.columns(3)
    col1.metric("Total Policies", total_policies)
    col2.metric("Avg Compliance Score", f"{avg_score:.1f}%" if gap_results else "N/A")
    col3.metric("Open Gaps", len(open_gaps))

    if open_gaps:
        st.subheader("Open Gaps (Missing Controls)")
        for gap in open_gaps:
            st.write(f"- **{gap['control_id']}**: {gap.get('reason', 'No reason provided')}")

    report_md = _build_audit_report_md(total_policies, avg_score, open_gaps, org_id)
    st.download_button(
        label="Export Audit Report (.md)",
        data=report_md,
        file_name="audit_report.md",
        mime="text/markdown",
    )


def _build_audit_report_md(total_policies, avg_score, open_gaps, org_id) -> str:
    from datetime import date

    lines = [
        "# Regulatory Compliance Audit Report",
        "",
        f"**Date:** {date.today().isoformat()}",
        f"**Organization ID:** {org_id or 'N/A'}",
        "",
        "## Summary",
        "",
        "| Metric | Value |",
        "|--------|-------|",
        f"| Total Policies | {total_policies} |",
        f"| Average Compliance Score | {avg_score:.1f}% |",
        f"| Open Gaps | {len(open_gaps)} |",
        "",
    ]

    if open_gaps:
        lines += ["## Open Gaps", ""]
        for gap in open_gaps:
            lines.append(f"- **{gap['control_id']}**: {gap.get('reason', '')}")
        lines.append("")

    lines += ["---", "_Generated by Regulatory AI Copilot_"]
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _get_org_slug(org_id) -> str:
    if not org_id:
        return None
    try:
        from services.db.session import session_scope
        from models.organization import Organization

        with session_scope() as db:
            org = db.query(Organization).filter(Organization.id == org_id).first()
            return org.slug if org else None
    except Exception:
        return None


# ---------------------------------------------------------------------------
# Main entry point
# ---------------------------------------------------------------------------

def render_app() -> None:
    st.set_page_config(
        page_title=APP_TITLE,
        layout="wide",
        initial_sidebar_state="expanded",
    )
    _ensure_app_directories()

    from services.auth.session import require_login, get_current_org_id, get_current_user_id, logout
    from services.llm.context import set_llm_context

    if not require_login():
        st.stop()

    org_id = get_current_org_id()
    user_id = get_current_user_id()
    set_llm_context(org_id, user_id)

    with st.sidebar:
        st.title(APP_TITLE)
        st.write("---")
        step = st.radio(
            "Navigation",
            options=STEP_LABELS,
            index=st.session_state.get("current_step_idx", 0),
        )
        st.session_state["current_step_idx"] = STEP_LABELS.index(step)
        st.write("---")
        if st.button("Sign out"):
            logout()
            st.rerun()

    step_idx = st.session_state.get("current_step_idx", 0)
    if step_idx == 0:
        _render_step1_business_profile()
    elif step_idx == 1:
        _render_step2_compliance_work()
    elif step_idx == 2:
        _render_step3_policy_vault()
    elif step_idx == 3:
        _render_step4_audit_report()


render_app()
