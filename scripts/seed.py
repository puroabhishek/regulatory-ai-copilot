"""Seed the database with the company admin org and superadmin user.

Run once on first boot:
    python scripts/seed.py
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from services.db.session import create_all_tables, session_scope
from services.auth.passwords import hash_password
from models.organization import Organization, User
from models.app_settings import AppSetting


COMPANY_ORG = {
    "name": "Regulatory AI Copilot (Company)",
    "slug": "company",
    "legal_name": "Regulatory AI Copilot",
    "country": "QA",
    "is_active": True,
}

SUPERADMIN = {
    "email": "admin@regai.local",
    "full_name": "Super Admin",
    "role": "superadmin",
    "password": "ChangeMe123!",
}

DEFAULT_SETTINGS = [
    ("eval_pass_threshold", "90.0", "Minimum pass rate % required before shipping (gap analysis)"),
    ("default_llm_model", "", "Override DEFAULT_LLM_MODEL from .env"),
    ("feature_feedback_enabled", "true", "Enable thumbs up/down feedback on outputs"),
    ("max_reference_excerpt_chars", "1500", "Max chars injected from reference policy into generation prompt"),
]


def seed():
    print("Creating tables...")
    create_all_tables()

    with session_scope() as db:
        # Company org
        org = db.query(Organization).filter_by(slug="company").first()
        if not org:
            org = Organization(**COMPANY_ORG)
            db.add(org)
            db.flush()
            print(f"Created org: {org.name}")
        else:
            print(f"Org already exists: {org.name}")

        # Superadmin user
        user = db.query(User).filter_by(email=SUPERADMIN["email"]).first()
        if not user:
            user = User(
                organization_id=org.id,
                email=SUPERADMIN["email"],
                full_name=SUPERADMIN["full_name"],
                role=SUPERADMIN["role"],
                password_hash=hash_password(SUPERADMIN["password"]),
                is_active=True,
            )
            db.add(user)
            print(f"Created superadmin: {user.email} / password: {SUPERADMIN['password']}")
        else:
            print(f"Superadmin already exists: {user.email}")

        # Default app settings
        for key, value, description in DEFAULT_SETTINGS:
            setting = db.query(AppSetting).filter_by(key=key).first()
            if not setting:
                db.add(AppSetting(key=key, value=value, description=description))
                print(f"Setting created: {key} = {value!r}")

    print("\nSeed complete.")
    print(f"Admin login: {SUPERADMIN['email']} / {SUPERADMIN['password']}")
    print("Change the password immediately after first login.")


if __name__ == "__main__":
    seed()
