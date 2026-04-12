import json
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Dict, Any, List


@dataclass
class BusinessProfile:
    profile_name: str

    # ---- Business & Operating Model ----
    country: str = "Qatar"
    regulator: str = "QCB"

    sector: str = "Fintech"  # Fintech / Telecom / Healthcare / Gov / Other
    business_type: str = "Lending"  # Lending / Insurance / Payments / SaaS / Tech Service Provider / Other
    business_model: str = "B2B"  # B2B / B2C / B2B2C / Other

    target_customers: str = "SMEs"
    other_users: str = ""
    key_stakeholders: str = ""

    # ---- Lending-specific ----
    performs_kyc: str = "Yes"  # Yes / No / Partner does it / Not sure
    mandated_kyc: str = "Yes"  # Yes / No / Not sure
    lending_model: str = "Partner-led"  # Own books / Partner-led / Mixed / Not applicable
    lending_partners: str = ""

    # ---- Cloud & Tech ----
    cloud_use: str = "Yes"
    cloud_service_model: str = "SaaS"
    cloud_providers: List[str] = field(default_factory=list)
    hosting_region: str = "Qatar"
    data_residency_required: str = "Yes"

    # ---- Data types ----
    handles_pii: str = "Yes"
    handles_financial_data: str = "Yes"
    handles_health_data: str = "No"
    handles_biometrics: str = "No"

    # ---- Security posture ----
    iam_maturity: str = "Basic"
    encryption_at_rest: str = "Yes"
    encryption_in_transit: str = "Yes"
    key_management: str = "CSP-managed"
    logging_monitoring: str = "Basic"
    vulnerability_mgmt: str = "Basic"
    penetration_testing: str = "No"
    sdlc_controls: str = "Basic"

    # ---- Vendors / Outsourcing ----
    uses_third_parties: str = "Yes"
    sub_processors_possible: str = "Yes"
    vendor_due_diligence: str = "Basic"

    # ---- Governance / Ops ----
    has_risk_register: str = "No"
    has_cloud_register: str = "No"
    has_audit_plan: str = "No"
    applicable_regulations: List[str] = field(default_factory=list)
    recommended_regulations: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        d = asdict(self)
        return d


def save_profile(profile: BusinessProfile, out_path: str) -> str:
    """
    What it does:
    - Saves the business profile as JSON to disk.
    Why:
    - So your policy/generator can reuse the same business context repeatedly.
    """
    Path(out_path).parent.mkdir(parents=True, exist_ok=True)
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(profile.to_dict(), f, ensure_ascii=False, indent=2)
    return out_path


def load_profile(path: str) -> Dict[str, Any]:
    """
    What it does:
    - Loads a previously saved profile JSON.
    Why:
    - So Streamlit can preview it and generator can use it.
    """
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)
    data.setdefault("cloud_providers", [])
    data.setdefault("applicable_regulations", [])
    data.setdefault("recommended_regulations", [])
    return data


def list_profiles(profile_dir: str = "data/profiles") -> List[str]:
    """
    What it does:
    - Lists all saved profiles (json files).
    Why:
    - So user can pick and reuse profiles in UI.
    """
    p = Path(profile_dir)
    if not p.exists():
        return []
    return sorted([x.name for x in p.glob("*.json")])
