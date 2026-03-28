"""Workflow helpers for blueprint authoring and artifact generation."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List, Optional

from core.blueprint import (
    build_blueprint,
    list_blueprints,
    list_reference_policies,
    load_blueprint,
    load_reference_policy,
    save_blueprint,
    save_reference_policy,
)
from core.control_registry import map_controls_to_company
from core.generator import (
    build_audit_register_rows,
    build_project_plan_rows,
    build_traceability_rows,
    generate_policy_md_from_blueprint,
    load_json,
    merge_controls,
    normalize_policy_name,
    save_csv,
    save_generation_run,
    save_text,
)
from core.profiler import list_profiles, load_profile


CONTROLS_DIR = Path("data/controls")
PROFILES_DIR = Path("data/profiles")
REFERENCES_DIR = Path("data/references")
BLUEPRINTS_DIR = Path("data/blueprints")
ARTIFACTS_DIR = Path("data/artifacts")


def list_policy_blueprint_inputs(
    controls_dir: str = str(CONTROLS_DIR),
    profiles_dir: str = str(PROFILES_DIR),
    refs_dir: str = str(REFERENCES_DIR),
) -> Dict[str, List[str]]:
    """Return the selectable inputs used by the blueprint-authoring page."""

    return {
        "control_files": sorted(path.name for path in Path(controls_dir).glob("*_controls.json")),
        "profile_files": sorted(list_profiles(profiles_dir)),
        "reference_files": list_reference_policies(refs_dir),
    }


def list_available_blueprints(blueprints_dir: str = str(BLUEPRINTS_DIR)) -> List[str]:
    """Return saved blueprint files."""

    return list_blueprints(blueprints_dir)


def list_generated_artifacts(artifacts_dir: str = str(ARTIFACTS_DIR)) -> List[str]:
    """Return generated artifact files for the artifact page."""

    directory = Path(artifacts_dir)
    if not directory.exists():
        return []
    return sorted(path.name for path in directory.glob("*") if path.is_file())


def load_reference_policy_text(reference_name: str, refs_dir: str = str(REFERENCES_DIR)) -> str:
    """Load a saved reference policy body by file name."""

    return load_reference_policy(str(Path(refs_dir) / reference_name))


def save_reference_policy_text(name: str, content: str) -> str:
    """Persist editable reference-policy text for later blueprint authoring."""

    return save_reference_policy(name, content)


def create_policy_blueprint(
    policy_name: str,
    selected_control_files: List[str],
    selected_profile_file: str,
    sample_policy_text: str,
    drafting_instructions: str,
    profiles_dir: str = str(PROFILES_DIR),
    blueprints_dir: str = str(BLUEPRINTS_DIR),
) -> Dict[str, Any]:
    """Build and save a policy blueprint from the selected inputs."""

    profile_data = load_profile(str(Path(profiles_dir) / selected_profile_file))
    blueprint = build_blueprint(
        policy_name=policy_name,
        selected_control_files=selected_control_files,
        selected_profile_file=selected_profile_file,
        profile_data=profile_data,
        sample_policy_text=sample_policy_text,
        drafting_instructions=drafting_instructions,
    )

    safe_name = policy_name.strip().replace(" ", "_")
    out_path = str(Path(blueprints_dir) / f"{safe_name}_blueprint.json")
    save_blueprint(blueprint, out_path)

    return {
        "blueprint": blueprint,
        "out_path": out_path,
    }


def generate_artifacts_from_blueprint(
    selected_blueprint: str,
    blueprints_dir: str = str(BLUEPRINTS_DIR),
    controls_dir: str = str(CONTROLS_DIR),
    artifacts_dir: str = str(ARTIFACTS_DIR),
    model: Optional[str] = None,
) -> Dict[str, Any]:
    """Load a blueprint, generate artifacts, save them, and return page-ready data."""

    blueprint = load_blueprint(str(Path(blueprints_dir) / selected_blueprint))
    control_sets = []
    selected_control_files = blueprint.get("selected_control_files", [])

    for file_name in selected_control_files:
        control_sets.append(load_json(str(Path(controls_dir) / file_name)))

    merged_controls = merge_controls(control_sets, selected_control_files)
    company_control_rows = map_controls_to_company(blueprint.get("profile_summary", {}), merged_controls)

    policy_name = blueprint.get("policy_name", "")
    policy_slug = normalize_policy_name(policy_name)

    policy_md = generate_policy_md_from_blueprint(
        blueprint=blueprint,
        controls=merged_controls,
        model=model,
    )

    plan_rows = build_project_plan_rows(policy_name, merged_controls, blueprint.get("profile_summary", {}))
    audit_rows = build_audit_register_rows(policy_name, merged_controls, blueprint.get("profile_summary", {}))
    trace_rows = build_traceability_rows(policy_name, merged_controls, blueprint.get("profile_summary", {}))

    artifacts_path = Path(artifacts_dir)
    policy_path = str(artifacts_path / f"{policy_slug}.md")
    plan_path = str(artifacts_path / f"{policy_slug}_implementation_plan.csv")
    audit_path = str(artifacts_path / f"{policy_slug}_audit_register.csv")
    trace_path = str(artifacts_path / f"{policy_slug}_traceability_matrix.csv")

    save_text(policy_path, policy_md)
    save_csv(plan_path, plan_rows)
    save_csv(audit_path, audit_rows)
    save_csv(trace_path, trace_rows)
    run_path = save_generation_run(policy_slug, blueprint, policy_md)

    return {
        "blueprint": blueprint,
        "policy_name": policy_name,
        "policy_slug": policy_slug,
        "merged_controls": merged_controls,
        "company_control_rows": company_control_rows,
        "policy_md": policy_md,
        "plan_rows": plan_rows,
        "audit_rows": audit_rows,
        "trace_rows": trace_rows,
        "policy_path": policy_path,
        "plan_path": plan_path,
        "audit_path": audit_path,
        "trace_path": trace_path,
        "run_path": run_path,
    }
