import sys
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

import streamlit as st

from services.llm.health import default_ollama_api_url, ensure_ollama_ready


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
    "9) Classification Admin",
]
OLLAMA_STATUS_SESSION_KEY = "_ollama_status"
OLLAMA_AUTOSTART_ATTEMPTED_SESSION_KEY = "_ollama_autostart_attempted"
OLLAMA_REQUIRED_PURPOSES = [
    "default",
    "control_classifier",
    "gap_analysis",
    "policy_generation",
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
    from app.pages.classification_admin_page import render_classification_admin_page
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
        render_classification_admin_page,
    ]


def _get_ollama_status() -> dict:
    """Check Ollama once per session and auto-launch the local app when helpful."""

    cached_status = st.session_state.get(OLLAMA_STATUS_SESSION_KEY)
    if cached_status and cached_status.get("ok"):
        return cached_status

    allow_autostart = not st.session_state.get(OLLAMA_AUTOSTART_ATTEMPTED_SESSION_KEY, False)
    status = ensure_ollama_ready(
        api_url=default_ollama_api_url(),
        purposes=OLLAMA_REQUIRED_PURPOSES,
        allow_autostart=allow_autostart,
    )

    if status.get("autostart_attempted"):
        st.session_state[OLLAMA_AUTOSTART_ATTEMPTED_SESSION_KEY] = True

    st.session_state[OLLAMA_STATUS_SESSION_KEY] = status
    return status


def _render_ollama_status_banner() -> None:
    """Show a concise startup banner about local Ollama availability."""

    try:
        status = _get_ollama_status()
    except Exception as exc:
        st.warning(f"Unable to check Ollama startup health: {type(exc).__name__}: {exc}")
        return

    autostart_message = str(status.get("autostart_message", "") or "").strip()
    if autostart_message and status.get("ok"):
        st.info(autostart_message)

    if status.get("ok"):
        st.caption(f"LLM status: ready using model `{status.get('configured_model', '')}`")
        return

    warning_lines = [str(status.get("message", "Ollama is unavailable."))]
    if autostart_message and not status.get("ok"):
        warning_lines.append(autostart_message)

    missing_models = status.get("missing_models", []) or []
    for model_name in missing_models:
        warning_lines.append(f"Try: `ollama pull {model_name}`")

    warning_lines.append("You can still use non-LLM tabs, but drafting and analysis features may fail until Ollama is ready.")
    st.warning("\n\n".join(warning_lines))


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
    _render_ollama_status_banner()

    for tab, render_page in zip(st.tabs(TAB_LABELS), page_renderers):
        with tab:
            render_page()


render_app()
