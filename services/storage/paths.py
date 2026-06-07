"""Org-scoped path resolver for local file storage."""
from pathlib import Path
from typing import Optional

_BASE = Path("data")


def org_data_dir(org_slug: Optional[str]) -> Path:
    if org_slug:
        return _BASE / "orgs" / org_slug
    return _BASE


def profiles_dir(org_slug: Optional[str]) -> Path:
    return org_data_dir(org_slug) / "profiles"


def blueprints_dir(org_slug: Optional[str]) -> Path:
    return org_data_dir(org_slug) / "blueprints"


def samples_dir(org_slug: Optional[str]) -> Path:
    return org_data_dir(org_slug) / "samples"


def artifacts_dir(org_slug: Optional[str]) -> Path:
    return org_data_dir(org_slug) / "artifacts"


def controls_dir(org_slug: Optional[str]) -> Path:
    return org_data_dir(org_slug) / "controls"


def gap_analysis_dir(org_slug: Optional[str]) -> Path:
    return org_data_dir(org_slug) / "gap_analysis"


def generation_runs_dir(org_slug: Optional[str]) -> Path:
    return org_data_dir(org_slug) / "generation_runs"


def ensure_org_dirs(org_slug: Optional[str]) -> None:
    """Create all org-scoped directories on first use."""
    for d in [profiles_dir, blueprints_dir, samples_dir, artifacts_dir,
              controls_dir, gap_analysis_dir, generation_runs_dir]:
        d(org_slug).mkdir(parents=True, exist_ok=True)
