import sys
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

import streamlit as st


APP_TITLE = "📘 Regulatory AI Copilot"
TAB_LABELS = [
    "1) Upload & Save",
    "2) Index & Search",
    "3) Controls",
    "4) Business Profile",
    "5) Policy Blueprint",
    "6) Artifact Generator",
    "7) Control Registry",
    "8) Policy Gap Analyzer",
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


def _ensure_app_directories() -> None:
    """Create the app data directories required by the page workflows."""
    for directory in DATA_DIRECTORIES:
        Path(directory).mkdir(parents=True, exist_ok=True)


def _load_page_renderers():
    """Import page renderers lazily so ui.py stays a thin shell."""
    from app.pages.artifact_generator_page import render_artifact_generator_page
    from app.pages.business_profile_page import render_business_profile_page
    from app.pages.control_registry_page import render_control_registry_page
    from app.pages.controls_page import render_controls_page
    from app.pages.gap_analysis_page import render_gap_analysis_page
    from app.pages.index_search_page import render_index_search_page
    from app.pages.policy_blueprint_page import render_policy_blueprint_page
    from app.pages.upload_save_page import render_upload_save_page

    return [
        render_upload_save_page,
        render_index_search_page,
        render_controls_page,
        render_business_profile_page,
        render_policy_blueprint_page,
        render_artifact_generator_page,
        render_control_registry_page,
        render_gap_analysis_page,
    ]


def render_app() -> None:
    """Initialize the app shell and dispatch to the page renderers."""
    st.set_page_config(page_title="Regulatory AI Copilot", layout="wide")
    _ensure_app_directories()

    try:
        page_renderers = _load_page_renderers()
    except Exception as exc:
        st.title("🚨 App crashed during import")
        st.exception(exc)
        st.stop()

    st.title(APP_TITLE)

    for tab, render_page in zip(st.tabs(TAB_LABELS), page_renderers):
        with tab:
            render_page()


render_app()
