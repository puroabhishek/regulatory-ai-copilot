"""Auth session helpers for Streamlit apps."""
from __future__ import annotations
from typing import Optional
import streamlit as st
from services.db.session import session_scope
from models.organization import User, Organization

_USER_KEY = "_auth_user_id"
_ORG_KEY = "_auth_org_id"
_ROLE_KEY = "_auth_role"


def set_current_user(user_id: str, org_id: Optional[str], role: str) -> None:
    st.session_state[_USER_KEY] = user_id
    st.session_state[_ORG_KEY] = org_id
    st.session_state[_ROLE_KEY] = role


def get_current_user_id() -> Optional[str]:
    return st.session_state.get(_USER_KEY)


def get_current_org_id() -> Optional[str]:
    return st.session_state.get(_ORG_KEY)


def get_current_role() -> Optional[str]:
    return st.session_state.get(_ROLE_KEY)


def is_authenticated() -> bool:
    return bool(st.session_state.get(_USER_KEY))


def logout() -> None:
    for key in [_USER_KEY, _ORG_KEY, _ROLE_KEY]:
        st.session_state.pop(key, None)


def require_login() -> bool:
    """Return True if authenticated. Show login form and return False otherwise."""
    if is_authenticated():
        return True
    _render_login_form()
    return False


def require_role(role: str) -> bool:
    current = get_current_role() or ""
    role_rank = {"user": 0, "org_admin": 1, "admin": 2, "superadmin": 3}
    return role_rank.get(current, -1) >= role_rank.get(role, 99)


def _render_login_form(admin_only: bool = False) -> None:
    from services.auth.passwords import verify_password
    from datetime import datetime, timezone

    st.title("🔐 Regulatory AI Copilot")
    st.subheader("Sign in to continue")

    with st.form("login_form"):
        identifier = st.text_input("Email or phone number")
        password = st.text_input("Password", type="password")
        submitted = st.form_submit_button("Sign in")

    if not submitted:
        st.stop()

    identifier = identifier.strip()
    if not identifier or not password:
        st.error("Email/phone and password are required.")
        st.stop()

    with session_scope() as db:
        user = (
            db.query(User)
            .filter(
                (User.email == identifier) | (User.phone == identifier),
                User.is_active == True,
            )
            .first()
        )

        if not user or not user.password_hash:
            st.error("Invalid credentials.")
            st.stop()

        if not verify_password(password, user.password_hash):
            st.error("Invalid credentials.")
            st.stop()

        if admin_only and (user.role or "") not in ("admin", "superadmin"):
            st.error("Admin access required.")
            st.stop()

        user.last_login_at = datetime.now(timezone.utc).isoformat()
        set_current_user(user.id, user.organization_id, user.role or "user")

    st.rerun()


def render_admin_login() -> bool:
    """Show admin login gate. Returns True if authenticated admin."""
    if is_authenticated() and require_role("admin"):
        return True
    _render_login_form(admin_only=True)
    return False
