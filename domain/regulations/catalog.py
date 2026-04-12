"""Catalog and recommendation helpers for profile-linked regulations.

This module keeps a small curated regulation catalog close to the product so
the UI can recommend likely obligations from a saved business profile and
resolve those recommendations back to existing control files when available.
"""

from __future__ import annotations

from copy import deepcopy
from pathlib import Path
from typing import Any, Dict, List


DEFAULT_CONTROLS_DIR = Path("data/controls")

REGULATION_CATALOG: List[Dict[str, Any]] = [
    {
        "title": "QCB Data Handling and Protection Regulation",
        "kind": "Regulation",
        "jurisdiction": "Qatar",
        "regulator": "QCB",
        "summary": "Data handling, protection, governance, and operational safeguards for regulated entities.",
        "control_file": "data_handling_and_protection_regulation_controls.json",
    },
    {
        "title": "QCB Cloud Computing Regulation",
        "kind": "Regulation",
        "jurisdiction": "Qatar",
        "regulator": "QCB",
        "summary": "Requirements for cloud adoption, outsourcing oversight, security, and accountability.",
        "control_file": "cloud_computing_regulation_controls.json",
    },
    {
        "title": "QCB eKYC Regulation",
        "kind": "Guideline",
        "jurisdiction": "Qatar",
        "regulator": "QCB",
        "summary": "Identity verification and electronic know-your-customer obligations for onboarding journeys.",
        "control_file": "qcb_-_ekyc_regulation_controls.json",
    },
    {
        "title": "Qatar Personal Data Privacy Law (Law No. 13 of 2016)",
        "kind": "Law",
        "jurisdiction": "Qatar",
        "regulator": "State of Qatar / NCSA",
        "summary": "Core privacy, lawful processing, protection, and individual-rights obligations for personal data.",
        "control_file": "ncsa-ncgaa-law_no._(13)_of_2016__on_protecting_personal_data_privacy_-_english_controls.json",
    },
    {
        "title": "National Data Classification Policy v3.0",
        "kind": "Policy",
        "jurisdiction": "Qatar",
        "regulator": "NCSA / CSGA",
        "summary": "Data classification, labeling, handling, and governance expectations for organizational information assets.",
        "control_file": "ncsa_csga_national_data_classification_policy_en_v3.0_controls.json",
    },
]


def _normalized(value: Any) -> str:
    return str(value or "").strip().lower()


def _is_yes(value: Any) -> bool:
    return _normalized(value) == "yes"


def _catalog_entry_map() -> Dict[str, Dict[str, Any]]:
    return {entry["title"]: entry for entry in REGULATION_CATALOG}


def list_regulation_catalog(controls_dir: str = str(DEFAULT_CONTROLS_DIR)) -> List[Dict[str, Any]]:
    """Return catalog entries enriched with local control-file availability."""

    directory = Path(controls_dir)
    entries: List[Dict[str, Any]] = []
    for item in REGULATION_CATALOG:
        enriched = deepcopy(item)
        control_file = str(item.get("control_file", "") or "").strip()
        enriched["control_file_available"] = bool(control_file and (directory / control_file).exists())
        entries.append(enriched)
    return entries


def get_regulation_catalog_titles() -> List[str]:
    """Return catalog titles in a stable UI-friendly order."""

    return [entry["title"] for entry in REGULATION_CATALOG]


def get_regulation_catalog_entry(title: str, controls_dir: str = str(DEFAULT_CONTROLS_DIR)) -> Dict[str, Any]:
    """Return one catalog entry with control-file availability metadata."""

    entry = deepcopy(_catalog_entry_map().get(title, {"title": title, "kind": "Custom"}))
    control_file = str(entry.get("control_file", "") or "").strip()
    entry["control_file_available"] = bool(control_file and (Path(controls_dir) / control_file).exists())
    return entry


def recommend_regulations_for_profile(
    profile: Dict[str, Any],
    controls_dir: str = str(DEFAULT_CONTROLS_DIR),
) -> List[Dict[str, Any]]:
    """Recommend likely regulations and guidelines for a business profile."""

    recommendations: Dict[str, Dict[str, Any]] = {}

    def add(title: str, reason: str) -> None:
        base = get_regulation_catalog_entry(title, controls_dir=controls_dir)
        recommendation = recommendations.setdefault(
            title,
            {
                **base,
                "reasons": [],
            },
        )
        if reason not in recommendation["reasons"]:
            recommendation["reasons"].append(reason)

    country = _normalized(profile.get("country"))
    regulator = _normalized(profile.get("regulator"))
    sector = _normalized(profile.get("sector"))
    business_type = _normalized(profile.get("business_type"))
    cloud_use = _is_yes(profile.get("cloud_use"))
    handles_pii = _is_yes(profile.get("handles_pii"))
    handles_financial_data = _is_yes(profile.get("handles_financial_data"))
    performs_kyc = _is_yes(profile.get("performs_kyc"))
    mandated_kyc = _is_yes(profile.get("mandated_kyc"))

    if country == "qatar":
        if handles_pii or handles_financial_data:
            add(
                "Qatar Personal Data Privacy Law (Law No. 13 of 2016)",
                "The profile indicates personal or regulated business data is handled in Qatar.",
            )
        if handles_pii or handles_financial_data:
            add(
                "National Data Classification Policy v3.0",
                "The profile handles data that should be classified, labeled, and protected consistently.",
            )

        if regulator == "qcb" or sector == "fintech" or business_type in {"lending", "payments", "insurance"}:
            add(
                "QCB Data Handling and Protection Regulation",
                "The profile looks like a QCB-regulated or financial-services business.",
            )

        if cloud_use and (regulator == "qcb" or sector == "fintech" or business_type in {"lending", "payments", "insurance", "saas"}):
            add(
                "QCB Cloud Computing Regulation",
                "The profile uses cloud services in a regulated operating environment.",
            )

        if performs_kyc or mandated_kyc or business_type in {"lending", "payments"}:
            add(
                "QCB eKYC Regulation",
                "The profile performs or depends on customer onboarding and KYC journeys.",
            )

    return list(recommendations.values())


def resolve_control_files_for_regulations(
    selected_regulations: List[str],
    controls_dir: str = str(DEFAULT_CONTROLS_DIR),
) -> Dict[str, List[str]]:
    """Resolve regulation titles to locally available control files."""

    directory = Path(controls_dir)
    resolved: List[str] = []
    missing: List[str] = []

    for title in selected_regulations:
        entry = _catalog_entry_map().get(title)
        control_file = str((entry or {}).get("control_file", "") or "").strip()
        if control_file and (directory / control_file).exists():
            if control_file not in resolved:
                resolved.append(control_file)
        else:
            missing.append(title)

    return {
        "control_files": resolved,
        "missing_regulations": missing,
    }
