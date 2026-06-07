"""Admin portal for the Regulatory AI Copilot."""
import sys
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

import streamlit as st

# ---------------------------------------------------------------------------
# Entry guard — admin login
# ---------------------------------------------------------------------------


def _render_admin_app() -> None:
    st.set_page_config(
        page_title="Regulatory AI Copilot — Admin",
        layout="wide",
        initial_sidebar_state="collapsed",
    )

    from services.auth.session import render_admin_login, get_current_org_id, get_current_user_id, logout
    from services.llm.context import set_llm_context

    if not render_admin_login():
        st.stop()

    org_id = get_current_org_id()
    user_id = get_current_user_id()
    set_llm_context(org_id, user_id)

    st.title("Admin Portal")

    with st.sidebar:
        if st.button("Sign out"):
            logout()
            st.rerun()

    tabs = st.tabs([
        "Control Registry",
        "Policy Version Library",
        "Eval Manager",
        "Prompt Manager",
        "Usage Analytics",
        "User & Org Management",
    ])

    with tabs[0]:
        _render_tab_control_registry()

    with tabs[1]:
        _render_tab_policy_version_library()

    with tabs[2]:
        _render_tab_eval_manager()

    with tabs[3]:
        _render_tab_prompt_manager()

    with tabs[4]:
        _render_tab_usage_analytics()

    with tabs[5]:
        _render_tab_user_org_management()


# ---------------------------------------------------------------------------
# Tab 1 — Control Registry
# ---------------------------------------------------------------------------

def _render_tab_control_registry() -> None:
    st.header("Control Registry")

    st.subheader("A. Upload Regulation")
    _render_control_registry_upload()

    st.divider()

    st.subheader("B. Browse Registry")
    _render_control_registry_browse()


def _render_control_registry_upload() -> None:
    regulation_name = st.text_input("Regulation Name", key="reg_name")
    regulation_version = st.text_input("Regulation Version", key="reg_version")
    issuing_body = st.text_input("Issuing Body", key="reg_issuing_body")

    uploaded = st.file_uploader("Upload PDF or CSV", type=["pdf", "csv"], key="reg_upload")

    if uploaded is None:
        return

    if uploaded.name.lower().endswith(".csv"):
        _handle_csv_upload(uploaded, regulation_name, regulation_version, issuing_body)
    elif uploaded.name.lower().endswith(".pdf"):
        _handle_pdf_upload(uploaded, regulation_name, regulation_version, issuing_body)


def _handle_csv_upload(uploaded_file, regulation_name, regulation_version, issuing_body) -> None:
    import pandas as pd

    try:
        df = pd.read_csv(uploaded_file)
    except Exception as exc:
        st.error(f"Could not parse CSV: {exc}")
        return

    st.write("**Preview:**")
    st.dataframe(df.head(5))

    cols = list(df.columns)
    expected_fields = [
        "control_statement",
        "clause_reference",
        "regulation_name",
        "control_type",
        "severity",
        "category",
    ]

    st.write("**Column Mapping:**")
    mapping = {}
    for field in expected_fields:
        default_idx = 0
        for j, col in enumerate(cols):
            if field.lower() in col.lower():
                default_idx = j
                break
        mapping[field] = st.selectbox(
            f"Map '{field}' to column:",
            options=["(skip)"] + cols,
            index=default_idx + 1 if default_idx < len(cols) else 0,
            key=f"csv_map_{field}",
        )

    if st.button("Save to Registry", key="csv_save"):
        if not regulation_name.strip():
            st.error("Please enter a regulation name before saving.")
            return
        _save_csv_controls_to_db(df, mapping, regulation_name, regulation_version, issuing_body)


def _save_csv_controls_to_db(df, mapping, regulation_name, regulation_version, issuing_body) -> None:
    try:
        import uuid as _uuid
        from services.db.session import session_scope
        from models.control_registry import RegistryControl

        def _val(row, field):
            col = mapping.get(field, "(skip)")
            if col == "(skip)" or col not in row:
                return None
            return str(row[col]).strip() if str(row[col]).strip() else None

        saved = 0
        with session_scope() as db:
            for _, row in df.iterrows():
                control = RegistryControl(
                    regulation_name=regulation_name.strip() or _val(row, "regulation_name"),
                    regulation_version=regulation_version.strip() or None,
                    issuing_body=issuing_body.strip() or None,
                    control_statement=_val(row, "control_statement"),
                    clause_reference=_val(row, "clause_reference"),
                    control_type=_val(row, "control_type"),
                    severity=_val(row, "severity"),
                    category=_val(row, "category"),
                    ingestion_source="csv",
                    is_active=True,
                )
                db.add(control)
                saved += 1
        st.success(f"Saved {saved} controls to the registry.")
    except Exception as exc:
        st.error(f"Failed to save controls: {exc}")


def _handle_pdf_upload(uploaded_file, regulation_name, regulation_version, issuing_body) -> None:
    try:
        import pypdf
        import io

        pdf_bytes = uploaded_file.read()
        reader = pypdf.PdfReader(io.BytesIO(pdf_bytes))
        text_pages = []
        for page in reader.pages:
            text_pages.append(page.extract_text() or "")
        full_text = "\n".join(text_pages)[:8000]
    except ImportError:
        st.error("pypdf is not installed. Please install it to process PDF files.")
        return
    except Exception as exc:
        st.error(f"Could not extract PDF text: {exc}")
        return

    st.write(f"Extracted {len(full_text)} characters from PDF.")

    if st.button("Extract Controls via AI", key="pdf_extract"):
        _extract_pdf_controls_with_llm(full_text, regulation_name, regulation_version, issuing_body)

    if st.session_state.get("pdf_extracted_controls"):
        _render_pdf_controls_preview(regulation_name, regulation_version, issuing_body)


def _extract_pdf_controls_with_llm(text, regulation_name, regulation_version, issuing_body) -> None:
    try:
        from services.llm.client import llm_json

        prompt = (
            "Extract all regulatory controls from the following text as a JSON array. "
            "Each element must have: clause_reference, control_statement, control_type, "
            "severity (high/medium/low), category, implementation_hint. "
            "Return only the JSON array, no extra text.\n\n"
            f"TEXT:\n{text}"
        )
        with st.spinner("Extracting controls with AI..."):
            result = llm_json(prompt=prompt, purpose="default")

        controls = result if isinstance(result, list) else result.get("controls", [])
        st.session_state["pdf_extracted_controls"] = controls
        st.success(f"Extracted {len(controls)} controls from PDF.")
    except Exception as exc:
        st.error(f"AI extraction failed: {exc}")


def _render_pdf_controls_preview(regulation_name, regulation_version, issuing_body) -> None:
    import pandas as pd

    controls = st.session_state["pdf_extracted_controls"]
    if not controls:
        return

    df = pd.DataFrame(controls)
    st.write("**Extracted Controls Preview:**")
    st.dataframe(df, use_container_width=True)

    if st.button("Save to Registry", key="pdf_save"):
        if not regulation_name.strip():
            st.error("Please enter a regulation name before saving.")
            return
        try:
            from services.db.session import session_scope
            from models.control_registry import RegistryControl

            saved = 0
            with session_scope() as db:
                for ctrl in controls:
                    db.add(RegistryControl(
                        regulation_name=regulation_name.strip(),
                        regulation_version=regulation_version.strip() or None,
                        issuing_body=issuing_body.strip() or None,
                        clause_reference=str(ctrl.get("clause_reference") or ""),
                        control_statement=str(ctrl.get("control_statement") or ""),
                        control_type=str(ctrl.get("control_type") or ""),
                        severity=str(ctrl.get("severity") or ""),
                        category=str(ctrl.get("category") or ""),
                        implementation_hint=str(ctrl.get("implementation_hint") or ""),
                        ingestion_source="pdf",
                        is_active=True,
                    ))
                    saved += 1
            st.success(f"Saved {saved} controls to the registry.")
            st.session_state.pop("pdf_extracted_controls", None)
        except Exception as exc:
            st.error(f"Failed to save controls: {exc}")


def _render_control_registry_browse() -> None:
    import pandas as pd

    try:
        from services.db.session import session_scope
        from models.control_registry import RegistryControl

        with session_scope() as db:
            controls = db.query(RegistryControl).filter(RegistryControl.is_active == True).all()
            rows = [
                {
                    "id": c.id,
                    "regulation_name": c.regulation_name or "",
                    "country": c.country or "",
                    "sector": c.sector or "",
                    "clause_reference": c.clause_reference or "",
                    "control_statement": (c.control_statement or "")[:80],
                    "severity": c.severity or "",
                    "category": c.category or "",
                }
                for c in controls
            ]
    except Exception as exc:
        st.error(f"Could not load registry: {exc}")
        return

    if not rows:
        st.info("No active controls in the registry.")
        return

    df = pd.DataFrame(rows)

    # Filters
    col1, col2, col3 = st.columns(3)
    with col1:
        country_filter = st.selectbox(
            "Filter by Country",
            options=["All"] + sorted(df["country"].dropna().unique().tolist()),
            key="browse_country",
        )
    with col2:
        sector_filter = st.selectbox(
            "Filter by Sector",
            options=["All"] + sorted(df["sector"].dropna().unique().tolist()),
            key="browse_sector",
        )
    with col3:
        reg_filter = st.selectbox(
            "Filter by Regulation",
            options=["All"] + sorted(df["regulation_name"].dropna().unique().tolist()),
            key="browse_reg",
        )

    filtered = df.copy()
    if country_filter != "All":
        filtered = filtered[filtered["country"] == country_filter]
    if sector_filter != "All":
        filtered = filtered[filtered["sector"] == sector_filter]
    if reg_filter != "All":
        filtered = filtered[filtered["regulation_name"] == reg_filter]

    st.dataframe(filtered.drop(columns=["id"]), use_container_width=True)

    # Deactivate per row
    st.write("**Deactivate a control:**")
    deactivate_id = st.text_input("Enter control ID to deactivate", key="deactivate_id")
    if st.button("Deactivate", key="deactivate_btn"):
        if deactivate_id.strip():
            try:
                from services.db.session import session_scope
                from models.control_registry import RegistryControl

                with session_scope() as db:
                    ctrl = db.query(RegistryControl).filter(RegistryControl.id == deactivate_id.strip()).first()
                    if ctrl:
                        ctrl.is_active = False
                        st.success(f"Control {deactivate_id} deactivated.")
                    else:
                        st.warning("Control not found.")
            except Exception as exc:
                st.error(f"Could not deactivate: {exc}")


# ---------------------------------------------------------------------------
# Tab 2 — Policy Version Library
# ---------------------------------------------------------------------------

def _render_tab_policy_version_library() -> None:
    st.header("Policy Version Library")

    _render_policy_version_upload()
    st.divider()
    _render_policy_version_table()


def _render_policy_version_upload() -> None:
    st.subheader("Upload Policy Version")

    uploaded = st.file_uploader(
        "Upload policy file (.md, .txt, .docx, .pdf)",
        type=["md", "txt", "docx", "pdf"],
        key="pv_upload",
    )
    policy_name = st.text_input("Policy Name", key="pv_policy_name")
    version_label = st.text_input("Version Label (e.g. v1.0)", key="pv_version_label")
    source_regulation = st.text_input("Source Regulation", key="pv_source_reg")
    qcb_status = st.selectbox(
        "QCB Status",
        options=["pending", "approved", "rejected", "partial"],
        key="pv_qcb_status",
    )
    qcb_feedback_notes = st.text_area("QCB Feedback Notes", key="pv_qcb_notes", height=80)
    qcb_feedback_date = st.date_input("QCB Feedback Date", key="pv_qcb_date")
    is_reference = st.checkbox("Mark as Reference Policy", key="pv_is_ref")

    if st.button("Save Policy Version", key="pv_save"):
        if not policy_name.strip():
            st.error("Policy name is required.")
            return
        _save_policy_version(
            uploaded,
            policy_name,
            version_label,
            source_regulation,
            qcb_status,
            qcb_feedback_notes,
            str(qcb_feedback_date),
            is_reference,
        )


def _save_policy_version(uploaded, policy_name, version_label, source_regulation,
                          qcb_status, qcb_feedback_notes, qcb_feedback_date, is_reference) -> None:
    from services.db.session import session_scope
    from models.policy_version import PolicyVersion
    from services.auth.session import get_current_user_id, get_current_org_id

    user_id = get_current_user_id()
    org_id = get_current_org_id()

    file_path = None
    policy_text = None

    if uploaded is not None:
        try:
            samples_dir = Path("data/samples")
            samples_dir.mkdir(parents=True, exist_ok=True)
            dest = samples_dir / uploaded.name
            file_bytes = uploaded.read()
            dest.write_bytes(file_bytes)
            file_path = str(dest)

            # Try to read as text
            if uploaded.name.lower().endswith((".md", ".txt")):
                policy_text = file_bytes.decode("utf-8", errors="replace")
            elif uploaded.name.lower().endswith(".pdf"):
                try:
                    import pypdf
                    import io
                    reader = pypdf.PdfReader(io.BytesIO(file_bytes))
                    policy_text = "\n".join(p.extract_text() or "" for p in reader.pages)
                except Exception:
                    policy_text = None
            elif uploaded.name.lower().endswith(".docx"):
                try:
                    import docx
                    import io
                    doc = docx.Document(io.BytesIO(file_bytes))
                    policy_text = "\n".join(para.text for para in doc.paragraphs)
                except Exception:
                    policy_text = None
        except Exception as exc:
            st.warning(f"Could not save file: {exc}")

    try:
        with session_scope() as db:
            pv = PolicyVersion(
                org_id=org_id,
                policy_name=policy_name.strip(),
                version_label=version_label.strip() or None,
                source_regulation=source_regulation.strip() or None,
                policy_text=policy_text,
                file_path=file_path,
                qcb_status=qcb_status,
                qcb_feedback_notes=qcb_feedback_notes.strip() or None,
                qcb_feedback_date=qcb_feedback_date or None,
                is_reference_policy=is_reference,
                uploaded_by_user_id=user_id,
            )
            db.add(pv)
        st.success(f"Policy version '{policy_name}' saved.")
    except Exception as exc:
        st.error(f"Failed to save policy version: {exc}")


def _render_policy_version_table() -> None:
    import pandas as pd

    st.subheader("Existing Policy Versions")

    STATUS_COLORS = {
        "approved": "green",
        "rejected": "red",
        "partial": "orange",
        "pending": "gray",
    }

    try:
        from services.db.session import session_scope
        from models.policy_version import PolicyVersion

        with session_scope() as db:
            versions = db.query(PolicyVersion).order_by(PolicyVersion.created_at.desc()).all()
            rows = [
                {
                    "ID": pv.id,
                    "Policy Name": pv.policy_name,
                    "Version": pv.version_label or "",
                    "Source Regulation": pv.source_regulation or "",
                    "QCB Status": pv.qcb_status or "pending",
                    "Reference": "Yes" if pv.is_reference_policy else "No",
                    "Created": str(pv.created_at or "")[:10],
                }
                for pv in versions
            ]
    except Exception as exc:
        st.error(f"Could not load policy versions: {exc}")
        return

    if not rows:
        st.info("No policy versions stored yet.")
        return

    df = pd.DataFrame(rows)
    st.dataframe(df, use_container_width=True)


# ---------------------------------------------------------------------------
# Tab 3 — Eval Manager
# ---------------------------------------------------------------------------

def _render_tab_eval_manager() -> None:
    st.header("Eval Manager")

    sub_nav = st.radio(
        "Section",
        options=["Cases", "Run Evals", "Results"],
        horizontal=True,
        key="eval_subnav",
    )

    if sub_nav == "Cases":
        _render_eval_cases()
    elif sub_nav == "Run Evals":
        _render_eval_run()
    elif sub_nav == "Results":
        _render_eval_results()


# ---- Cases ----

def _render_eval_cases() -> None:
    st.subheader("Eval Cases")

    case_tab_a, case_tab_b, case_tab_c = st.tabs(["Excel Import", "Manual Entry", "Browse Cases"])

    with case_tab_a:
        _render_eval_cases_excel_import()

    with case_tab_b:
        _render_eval_cases_manual_entry()

    with case_tab_c:
        _render_eval_cases_browse()


def _render_eval_cases_excel_import() -> None:
    st.write("**Import eval cases from Excel (.xlsx)**")

    uploaded = st.file_uploader("Upload .xlsx", type=["xlsx"], key="eval_xlsx_upload")
    if uploaded is None:
        return

    try:
        import pandas as pd
        df = pd.read_excel(uploaded)
    except Exception as exc:
        st.error(f"Could not parse Excel file: {exc}")
        return

    st.write("**Preview:**")
    st.dataframe(df.head(5))

    cols = list(df.columns)
    expected_fields = [
        "control_id",
        "control_statement",
        "expected_status",
        "reason_contains",
        "policy_ref",
    ]

    st.write("**Column Mapping:**")
    mapping = {}
    for field in expected_fields:
        default_idx = 0
        for j, col in enumerate(cols):
            if field.lower().replace("_", "") in col.lower().replace("_", ""):
                default_idx = j
                break
        mapping[field] = st.selectbox(
            f"'{field}' column:",
            options=["(skip)"] + cols,
            index=default_idx + 1 if default_idx < len(cols) else 0,
            key=f"eval_map_{field}",
        )

    STATUS_NORMALIZE = {
        "non-compliant": "Missing",
        "noncompliant": "Missing",
        "partially compliant": "Partially Covered",
        "partial": "Partially Covered",
        "covered": "Covered",
        "compliant": "Covered",
        "n/a": None,
        "na": None,
    }

    if st.button("Save Cases", key="eval_xlsx_save"):
        _save_excel_eval_cases(df, mapping, STATUS_NORMALIZE)


def _save_excel_eval_cases(df, mapping, status_normalize) -> None:
    from services.db.session import session_scope
    from models.eval_store import EvalCase
    from services.auth.session import get_current_user_id

    user_id = get_current_user_id()

    def _val(row, field):
        col = mapping.get(field, "(skip)")
        if col == "(skip)" or col not in row.index:
            return None
        v = row[col]
        if hasattr(v, "item"):
            v = v.item()
        return str(v).strip() if v is not None and str(v).strip() else None

    saved = skipped = 0
    try:
        with session_scope() as db:
            for _, row in df.iterrows():
                raw_status = (_val(row, "expected_status") or "").lower()
                normalized = status_normalize.get(raw_status, raw_status or None)
                if normalized is None:
                    skipped += 1
                    continue

                ctrl_id = _val(row, "control_id") or f"CTRL-{_ + 1}"
                ctrl_stmt = _val(row, "control_statement") or ""
                reason_kw = _val(row, "reason_contains") or ""

                case = EvalCase(
                    task="gap_analysis_coverage",
                    name=ctrl_id,
                    description=ctrl_stmt[:255] if ctrl_stmt else None,
                    input_data={
                        "control_id": ctrl_id,
                        "control_statement": ctrl_stmt,
                        "policy_ref": _val(row, "policy_ref") or "",
                    },
                    expected_output={
                        "status": normalized,
                        "reason_contains": [kw.strip() for kw in reason_kw.split(",") if kw.strip()],
                    },
                    source="excel_import",
                    created_by_user_id=user_id,
                )
                db.add(case)
                saved += 1
        st.success(f"Saved {saved} eval cases ({skipped} skipped due to N/A status).")
    except Exception as exc:
        st.error(f"Failed to save eval cases: {exc}")


def _render_eval_cases_manual_entry() -> None:
    st.write("**Add a case manually**")

    with st.form("manual_eval_case_form"):
        task = st.selectbox("Task", options=["gap_analysis_coverage", "policy_generation"], key="mec_task")
        name = st.text_input("Case Name", key="mec_name")
        description = st.text_area("Description", key="mec_desc", height=60)
        input_data = st.text_area("Input Data (JSON)", key="mec_input", height=100, value="{}")
        expected_output = st.text_area("Expected Output (JSON)", key="mec_expected", height=100, value="{}")
        submit = st.form_submit_button("Save Case")

    if submit:
        import json
        try:
            inp = json.loads(input_data)
            exp = json.loads(expected_output)
        except json.JSONDecodeError as exc:
            st.error(f"Invalid JSON: {exc}")
            return

        try:
            from services.db.session import session_scope
            from models.eval_store import EvalCase
            from services.auth.session import get_current_user_id

            with session_scope() as db:
                db.add(EvalCase(
                    task=task,
                    name=name.strip() or None,
                    description=description.strip() or None,
                    input_data=inp,
                    expected_output=exp,
                    source="manual",
                    created_by_user_id=get_current_user_id(),
                ))
            st.success("Eval case saved.")
        except Exception as exc:
            st.error(f"Failed to save case: {exc}")


def _render_eval_cases_browse() -> None:
    import pandas as pd

    try:
        from services.db.session import session_scope
        from models.eval_store import EvalCase

        with session_scope() as db:
            cases = db.query(EvalCase).filter(EvalCase.is_active == True).order_by(EvalCase.created_at.desc()).all()
            rows = [
                {
                    "ID": c.id,
                    "Task": c.task,
                    "Name": c.name or "",
                    "Source": c.source or "",
                    "Created": str(c.created_at or "")[:10],
                }
                for c in cases
            ]
    except Exception as exc:
        st.error(f"Could not load eval cases: {exc}")
        return

    if not rows:
        st.info("No eval cases stored yet.")
        return

    st.dataframe(pd.DataFrame(rows), use_container_width=True)


# ---- Run Evals ----

def _render_eval_run() -> None:
    st.subheader("Run Evals")

    task = st.selectbox("Task", options=["gap_analysis", "policy_generation"], key="er_task")
    model_override = st.text_input("Model Override (optional)", key="er_model")

    if st.button("Run Evals", key="er_run"):
        _execute_eval_run(task, model_override.strip() or None)


def _execute_eval_run(task: str, model_override) -> None:
    import json
    from services.db.session import session_scope
    from models.eval_store import EvalCase, EvalRun, EvalResult
    from services.auth.session import get_current_user_id, get_current_org_id
    from models.app_settings import AppSetting

    user_id = get_current_user_id()

    # Load threshold from AppSetting
    threshold = 0.8
    try:
        with session_scope() as db:
            setting = db.query(AppSetting).filter(AppSetting.key == "eval_pass_threshold").first()
            if setting and setting.value:
                threshold = float(setting.value)
    except Exception:
        pass

    # Load cases from DB
    try:
        with session_scope() as db:
            db_task = "gap_analysis_coverage" if task == "gap_analysis" else "policy_generation"
            cases = db.query(EvalCase).filter(
                EvalCase.task == db_task,
                EvalCase.is_active == True,
            ).all()
            cases_data = [
                {
                    "id": c.id,
                    "task": c.task,
                    "name": c.name,
                    "input_data": c.input_data or {},
                    "expected_output": c.expected_output or {},
                }
                for c in cases
            ]
    except Exception as exc:
        st.error(f"Could not load eval cases: {exc}")
        return

    if not cases_data:
        st.warning("No eval cases found for this task. Add cases in the 'Cases' section first.")
        return

    st.write(f"Running {len(cases_data)} cases for task '{task}'...")
    progress_bar = st.progress(0)
    status_text = st.empty()
    total = len(cases_data)

    results_list = []

    if task == "gap_analysis":
        from evals.runners.gap_eval_runner import GapEvalRunner
        from evals.runners.base_runner import EvalCase as RunnerCase

        runner = GapEvalRunner()
        for i, case_data in enumerate(cases_data):
            status_text.text(f"Running {i + 1}/{total}: {case_data.get('name', case_data['id'])}")
            runner_case = RunnerCase(
                id=case_data["id"],
                task=case_data["task"],
                input=case_data["input_data"],
                expected_output=case_data["expected_output"],
            )
            try:
                res = runner.run_case(runner_case)
                results_list.append({
                    "case_id": case_data["id"],
                    "case_name": case_data.get("name", ""),
                    "passed": res.passed,
                    "scores": res.scores,
                    "error": res.error,
                    "raw_output": res.raw_output,
                })
            except Exception as exc:
                results_list.append({
                    "case_id": case_data["id"],
                    "case_name": case_data.get("name", ""),
                    "passed": False,
                    "scores": {},
                    "error": str(exc),
                    "raw_output": None,
                })
            progress_bar.progress((i + 1) / total)
    else:
        st.warning(f"Eval runner for '{task}' is not yet configured in this UI.")
        return

    progress_bar.empty()
    status_text.empty()

    passed_count = sum(1 for r in results_list if r["passed"])
    failed_count = total - passed_count
    pass_rate = (passed_count / total * 100) if total > 0 else 0.0

    # Save run + results to DB
    try:
        with session_scope() as db:
            run = EvalRun(
                task=task,
                model_used=model_override or "(default)",
                total_cases=total,
                passed=passed_count,
                failed=failed_count,
                errored=sum(1 for r in results_list if r["error"]),
                pass_rate_pct=pass_rate,
                pass_threshold=threshold * 100,
                triggered_by_user_id=user_id,
            )
            db.add(run)
            db.flush()

            for r in results_list:
                db.add(EvalResult(
                    eval_run_id=run.id,
                    eval_case_id=r["case_id"],
                    raw_output=r["raw_output"],
                    scores=r["scores"],
                    passed=r["passed"],
                    error=r["error"],
                ))
        st.success(f"Eval run saved. Pass rate: {pass_rate:.1f}% (threshold: {threshold * 100:.1f}%)")
    except Exception as exc:
        st.error(f"Could not save eval run to DB: {exc}")

    if pass_rate >= threshold * 100:
        st.success(f"PASSED — {pass_rate:.1f}% >= {threshold * 100:.1f}% threshold")
    else:
        st.error(f"FAILED — {pass_rate:.1f}% < {threshold * 100:.1f}% threshold")

    # Show per-case results
    import pandas as pd
    df = pd.DataFrame([
        {
            "Case": r.get("case_name") or r["case_id"],
            "Passed": "Yes" if r["passed"] else "No",
            "Error": r.get("error") or "",
        }
        for r in results_list
    ])
    st.dataframe(df, use_container_width=True)


# ---- Results ----

def _render_eval_results() -> None:
    import pandas as pd

    st.subheader("Recent Eval Runs")

    try:
        from services.db.session import session_scope
        from models.eval_store import EvalRun, EvalResult, EvalCase

        with session_scope() as db:
            runs = db.query(EvalRun).order_by(EvalRun.created_at.desc()).limit(10).all()
            run_rows = [
                {
                    "ID": r.id,
                    "Task": r.task,
                    "Total": r.total_cases,
                    "Passed": r.passed,
                    "Failed": r.failed,
                    "Pass Rate": f"{r.pass_rate_pct or 0:.1f}%",
                    "Threshold": f"{r.pass_threshold or 0:.1f}%",
                    "Created": str(r.created_at or "")[:16],
                }
                for r in runs
            ]
    except Exception as exc:
        st.error(f"Could not load eval runs: {exc}")
        return

    if not run_rows:
        st.info("No eval runs yet.")
        return

    df_runs = pd.DataFrame(run_rows)
    st.dataframe(df_runs.drop(columns=["ID"]), use_container_width=True)

    selected_run_id = st.selectbox(
        "View results for run:",
        options=[r["ID"] for r in run_rows],
        format_func=lambda rid: next(
            (f"{r['Task']} — {r['Created']} ({r['Pass Rate']})" for r in run_rows if r["ID"] == rid),
            rid,
        ),
        key="er_select_run",
    )

    if selected_run_id:
        try:
            from services.db.session import session_scope
            from models.eval_store import EvalResult, EvalCase

            with session_scope() as db:
                results = (
                    db.query(EvalResult)
                    .filter(EvalResult.eval_run_id == selected_run_id)
                    .all()
                )
                result_rows = []
                for er in results:
                    case = db.query(EvalCase).filter(EvalCase.id == er.eval_case_id).first()
                    result_rows.append({
                        "Case Name": (case.name if case else er.eval_case_id) or er.eval_case_id,
                        "Passed": "Yes" if er.passed else "No",
                        "Scores": str(er.scores or {}),
                        "Error": er.error or "",
                    })
        except Exception as exc:
            st.error(f"Could not load results: {exc}")
            return

        if result_rows:
            st.dataframe(pd.DataFrame(result_rows), use_container_width=True)
        else:
            st.info("No results for this run.")


# ---------------------------------------------------------------------------
# Tab 4 — Prompt Manager
# ---------------------------------------------------------------------------

def _render_tab_prompt_manager() -> None:
    import hashlib

    st.header("Prompt Manager")

    prompts_root = Path("prompts")
    if not prompts_root.exists():
        st.warning("prompts/ directory not found.")
        return

    md_files = sorted(prompts_root.rglob("*.md"))
    if not md_files:
        st.info("No .md prompt files found.")
        return

    # Sidebar-style list
    file_options = [str(f.relative_to(prompts_root)) for f in md_files]
    selected_rel = st.selectbox("Select prompt file", options=file_options, key="pm_select")
    selected_path = prompts_root / selected_rel

    try:
        content = selected_path.read_text(encoding="utf-8")
    except Exception as exc:
        st.error(f"Could not read file: {exc}")
        return

    import os
    mtime = os.path.getmtime(selected_path)
    from datetime import datetime
    mtime_str = datetime.fromtimestamp(mtime).strftime("%Y-%m-%d %H:%M:%S")
    prompt_hash = hashlib.sha256(content.encode()).hexdigest()[:8]

    col1, col2 = st.columns(2)
    col1.write(f"**Last modified:** {mtime_str}")
    col2.write(f"**Prompt hash:** `{prompt_hash}`")

    st.write("**Preview (first 100 chars):**")
    st.code(content[:100] + ("..." if len(content) > 100 else ""), language="markdown")

    new_content = st.text_area(
        "Edit prompt",
        value=content,
        height=400,
        key=f"pm_edit_{selected_rel}",
    )

    if st.button("Save Prompt", key="pm_save"):
        try:
            selected_path.write_text(new_content, encoding="utf-8")
            st.success(f"Saved {selected_rel}")
        except Exception as exc:
            st.error(f"Could not save: {exc}")


# ---------------------------------------------------------------------------
# Tab 5 — Usage Analytics
# ---------------------------------------------------------------------------

def _render_tab_usage_analytics() -> None:
    import pandas as pd

    st.header("Usage Analytics")

    # --- Audit Logs by org ---
    st.subheader("LLM Call Counts by Organization")
    try:
        from services.db.session import session_scope
        from models.audit_log import AuditLog
        from sqlalchemy import func

        with session_scope() as db:
            rows = (
                db.query(
                    AuditLog.org_id,
                    func.count(AuditLog.id).label("calls"),
                    func.avg(AuditLog.duration_ms).label("avg_ms"),
                )
                .group_by(AuditLog.org_id)
                .all()
            )
            org_rows = [
                {
                    "Org ID": r.org_id or "(none)",
                    "Calls": r.calls,
                    "Avg Duration (ms)": round(r.avg_ms or 0, 1),
                }
                for r in rows
            ]
    except Exception as exc:
        st.error(f"Could not load audit logs: {exc}")
        org_rows = []

    if org_rows:
        st.dataframe(pd.DataFrame(org_rows), use_container_width=True)
    else:
        st.info("No audit log data yet.")

    # --- Feedback stats ---
    st.subheader("Output Feedback")
    try:
        from services.db.session import session_scope
        from models.feedback import OutputFeedback
        from sqlalchemy import func

        with session_scope() as db:
            positive = db.query(func.count(OutputFeedback.id)).filter(OutputFeedback.rating == "positive").scalar() or 0
            negative = db.query(func.count(OutputFeedback.id)).filter(OutputFeedback.rating == "negative").scalar() or 0
            reason_rows = (
                db.query(OutputFeedback.reason_code, func.count(OutputFeedback.id).label("cnt"))
                .filter(OutputFeedback.reason_code.isnot(None))
                .group_by(OutputFeedback.reason_code)
                .order_by(func.count(OutputFeedback.id).desc())
                .limit(10)
                .all()
            )
    except Exception as exc:
        st.error(f"Could not load feedback: {exc}")
        positive = negative = 0
        reason_rows = []

    col1, col2 = st.columns(2)
    col1.metric("Positive Feedback", positive)
    col2.metric("Negative Feedback", negative)

    if reason_rows:
        st.write("**Top Reason Codes:**")
        st.dataframe(
            pd.DataFrame([{"Reason Code": r.reason_code, "Count": r.cnt} for r in reason_rows]),
            use_container_width=True,
        )

    # --- Recent audit log ---
    st.subheader("Recent Audit Log (last 100 entries)")
    try:
        from services.db.session import session_scope
        from models.audit_log import AuditLog

        with session_scope() as db:
            logs = db.query(AuditLog).order_by(AuditLog.created_at.desc()).limit(100).all()
            log_rows = [
                {
                    "Time": str(l.created_at or "")[:16],
                    "Org": l.org_id or "",
                    "User": l.user_id or "",
                    "Action": l.action or "",
                    "Model": l.model_used or "",
                    "Duration (ms)": l.duration_ms or 0,
                    "Error": (l.error or "")[:60],
                }
                for l in logs
            ]
    except Exception as exc:
        st.error(f"Could not load recent logs: {exc}")
        log_rows = []

    if log_rows:
        st.dataframe(pd.DataFrame(log_rows), use_container_width=True, height=400)
    else:
        st.info("No audit log entries yet.")


# ---------------------------------------------------------------------------
# Tab 6 — User & Org Management
# ---------------------------------------------------------------------------

def _render_tab_user_org_management() -> None:
    st.header("User & Org Management")

    uom_tab1, uom_tab2, uom_tab3 = st.tabs(["Organizations", "Users", "App Settings"])

    with uom_tab1:
        _render_org_management()

    with uom_tab2:
        _render_user_management()

    with uom_tab3:
        _render_app_settings()


def _render_org_management() -> None:
    import pandas as pd

    st.subheader("Organizations")

    try:
        from services.db.session import session_scope
        from models.organization import Organization

        with session_scope() as db:
            orgs = db.query(Organization).order_by(Organization.created_at.desc()).all()
            rows = [
                {
                    "ID": o.id,
                    "Name": o.name,
                    "Slug": o.slug or "",
                    "Country": o.country or "",
                    "Active": "Yes" if o.is_active else "No",
                    "Created": str(o.created_at or "")[:10],
                }
                for o in orgs
            ]
    except Exception as exc:
        st.error(f"Could not load organizations: {exc}")
        rows = []

    if rows:
        st.dataframe(pd.DataFrame(rows), use_container_width=True)
    else:
        st.info("No organizations found.")

    st.subheader("Create New Organization")
    with st.form("create_org_form"):
        org_name = st.text_input("Organization Name", key="co_name")
        org_slug = st.text_input("Slug (unique identifier)", key="co_slug")
        org_country = st.text_input("Country", value="Qatar", key="co_country")
        submit = st.form_submit_button("Create Organization")

    if submit:
        if not org_name.strip():
            st.error("Organization name is required.")
            return
        try:
            from services.db.session import session_scope
            from models.organization import Organization

            with session_scope() as db:
                db.add(Organization(
                    name=org_name.strip(),
                    slug=org_slug.strip() or None,
                    country=org_country.strip() or None,
                ))
            st.success(f"Organization '{org_name}' created.")
        except Exception as exc:
            st.error(f"Could not create organization: {exc}")


def _render_user_management() -> None:
    import pandas as pd

    st.subheader("Users")

    try:
        from services.db.session import session_scope
        from models.organization import User, Organization

        with session_scope() as db:
            users = db.query(User).order_by(User.created_at.desc()).all()
            org_map = {o.id: o.name for o in db.query(Organization).all()}
            rows = [
                {
                    "ID": u.id,
                    "Email": u.email or "",
                    "Full Name": u.full_name or "",
                    "Role": u.role or "",
                    "Organization": org_map.get(u.organization_id or "", ""),
                    "Last Login": str(u.last_login_at or "")[:16],
                    "Active": "Yes" if u.is_active else "No",
                }
                for u in users
            ]
    except Exception as exc:
        st.error(f"Could not load users: {exc}")
        rows = []
        org_map = {}

    if rows:
        st.dataframe(pd.DataFrame(rows), use_container_width=True)
    else:
        st.info("No users found.")

    # Deactivate user
    deactivate_uid = st.text_input("Deactivate User by ID", key="deact_uid")
    if st.button("Deactivate User", key="deact_btn"):
        if deactivate_uid.strip():
            try:
                from services.db.session import session_scope
                from models.organization import User

                with session_scope() as db:
                    u = db.query(User).filter(User.id == deactivate_uid.strip()).first()
                    if u:
                        u.is_active = False
                        st.success(f"User {deactivate_uid} deactivated.")
                    else:
                        st.warning("User not found.")
            except Exception as exc:
                st.error(f"Could not deactivate user: {exc}")

    st.subheader("Create New User")
    try:
        from services.db.session import session_scope
        from models.organization import Organization

        with session_scope() as db:
            orgs = db.query(Organization).filter(Organization.is_active == True).all()
            org_options = {o.name: o.id for o in orgs}
    except Exception:
        org_options = {}

    with st.form("create_user_form"):
        email = st.text_input("Email", key="cu_email")
        phone = st.text_input("Phone (optional)", key="cu_phone")
        full_name = st.text_input("Full Name", key="cu_full_name")
        role = st.selectbox("Role", options=["user", "org_admin", "admin", "superadmin"], key="cu_role")
        password = st.text_input("Password", type="password", key="cu_password")
        org_choice = st.selectbox("Organization", options=list(org_options.keys()), key="cu_org") if org_options else st.text_input("Organization ID", key="cu_org_id")
        submit = st.form_submit_button("Create User")

    if submit:
        if not email.strip() or not password:
            st.error("Email and password are required.")
            return
        try:
            from services.db.session import session_scope
            from models.organization import User
            from services.auth.passwords import hash_password

            org_id = org_options.get(org_choice) if org_options else (org_choice or None)
            with session_scope() as db:
                db.add(User(
                    email=email.strip(),
                    phone=phone.strip() or None,
                    full_name=full_name.strip() or None,
                    role=role,
                    password_hash=hash_password(password),
                    organization_id=org_id,
                    is_active=True,
                ))
            st.success(f"User '{email}' created.")
        except Exception as exc:
            st.error(f"Could not create user: {exc}")


def _render_app_settings() -> None:
    st.subheader("App Settings")

    try:
        from services.db.session import session_scope
        from models.app_settings import AppSetting

        with session_scope() as db:
            settings = db.query(AppSetting).order_by(AppSetting.key).all()
            settings_data = [{"id": s.id, "key": s.key, "value": s.value or "", "description": s.description or ""} for s in settings]
    except Exception as exc:
        st.error(f"Could not load settings: {exc}")
        settings_data = []

    if not settings_data:
        st.info("No app settings configured yet.")

    updated_values = {}
    for s in settings_data:
        col1, col2 = st.columns([2, 3])
        col1.write(f"**{s['key']}**")
        if s["description"]:
            col1.caption(s["description"])
        new_val = col2.text_input(
            f"Value for {s['key']}",
            value=s["value"],
            key=f"setting_{s['id']}",
            label_visibility="collapsed",
        )
        updated_values[s["id"]] = new_val

    if settings_data and st.button("Save Settings", key="settings_save"):
        try:
            from services.db.session import session_scope
            from models.app_settings import AppSetting
            from services.auth.session import get_current_user_id

            user_id = get_current_user_id()
            with session_scope() as db:
                for sid, new_val in updated_values.items():
                    setting = db.query(AppSetting).filter(AppSetting.id == sid).first()
                    if setting:
                        setting.value = new_val
                        setting.updated_by_user_id = user_id
            st.success("Settings saved.")
        except Exception as exc:
            st.error(f"Could not save settings: {exc}")

    # Add new setting
    st.write("---")
    st.write("**Add New Setting:**")
    with st.form("add_setting_form"):
        new_key = st.text_input("Key", key="ns_key")
        new_value = st.text_input("Value", key="ns_value")
        new_desc = st.text_input("Description (optional)", key="ns_desc")
        add_submit = st.form_submit_button("Add Setting")

    if add_submit:
        if not new_key.strip():
            st.error("Key is required.")
            return
        try:
            from services.db.session import session_scope
            from models.app_settings import AppSetting
            from services.auth.session import get_current_user_id

            with session_scope() as db:
                db.add(AppSetting(
                    key=new_key.strip(),
                    value=new_value.strip() or None,
                    description=new_desc.strip() or None,
                    updated_by_user_id=get_current_user_id(),
                ))
            st.success(f"Setting '{new_key}' added.")
        except Exception as exc:
            st.error(f"Could not add setting: {exc}")


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

_render_admin_app()
