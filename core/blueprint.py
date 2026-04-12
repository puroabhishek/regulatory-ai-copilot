import json
from pathlib import Path
from typing import Any, Dict, List, Optional

from schemas.common import ensure_schema
from schemas.policy import Policy


def summarize_profile(profile: Dict[str, Any]) -> Dict[str, Any]:
    """
    Keep only the fields that should influence policy drafting.
    """
    return {
        "profile_name": profile.get("profile_name", ""),
        "country": profile.get("country", ""),
        "regulator": profile.get("regulator", ""),
        "sector": profile.get("sector", ""),
        "business_type": profile.get("business_type", ""),
        "business_model": profile.get("business_model", ""),
        "target_customers": profile.get("target_customers", ""),
        "other_users": profile.get("other_users", ""),
        "key_stakeholders": profile.get("key_stakeholders", ""),
        "performs_kyc": profile.get("performs_kyc", ""),
        "mandated_kyc": profile.get("mandated_kyc", ""),
        "lending_model": profile.get("lending_model", ""),
        "lending_partners": profile.get("lending_partners", ""),
        "cloud_use": profile.get("cloud_use", ""),
        "cloud_service_model": profile.get("cloud_service_model", ""),
        "cloud_providers": profile.get("cloud_providers", []),
        "hosting_region": profile.get("hosting_region", ""),
        "data_residency_required": profile.get("data_residency_required", ""),
        "handles_pii": profile.get("handles_pii", ""),
        "handles_financial_data": profile.get("handles_financial_data", ""),
        "applicable_regulations": profile.get("applicable_regulations", []),
        "recommended_regulations": profile.get("recommended_regulations", []),
    }


def build_blueprint(
    policy_name: str,
    selected_control_files: List[str],
    selected_profile_file: str,
    profile_data: Dict[str, Any],
    sample_policy_text: str,
    drafting_instructions: str,
    applicable_regulations: Optional[List[str]] = None,
    source_context: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    return Policy(
        policy_name=policy_name.strip(),
        selected_control_files=selected_control_files,
        applicable_regulations=applicable_regulations or [],
        selected_profile_file=selected_profile_file,
        profile_summary=summarize_profile(profile_data),
        sample_policy_text=sample_policy_text.strip(),
        drafting_instructions=drafting_instructions.strip(),
        source_context=source_context or {},
    ).to_dict()


def save_blueprint(blueprint: Dict[str, Any], out_path: str) -> str:
    Path(out_path).parent.mkdir(parents=True, exist_ok=True)
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(ensure_schema(blueprint, Policy).to_dict(), f, ensure_ascii=False, indent=2)
    return out_path


def load_blueprint(path: str) -> Dict[str, Any]:
    with open(path, "r", encoding="utf-8") as f:
        return ensure_schema(json.load(f), Policy).to_dict()


def list_blueprints(blueprint_dir: str = "data/blueprints") -> List[str]:
    p = Path(blueprint_dir)
    if not p.exists():
        return []
    return sorted([x.name for x in p.glob("*.json")])


def save_reference_policy(name: str, content: str) -> str:
    safe_name = name.strip().replace(" ", "_")
    out_path = Path("data/references") / f"{safe_name}.md"
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with open(out_path, "w", encoding="utf-8") as f:
        f.write(content)
    return str(out_path)


def list_reference_policies(ref_dir: str = "data/references") -> List[str]:
    p = Path(ref_dir)
    if not p.exists():
        return []
    return sorted([x.name for x in p.glob("*.md")])


def load_reference_policy(path: str) -> str:
    with open(path, "r", encoding="utf-8") as f:
        return f.read()
