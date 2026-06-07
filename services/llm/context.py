"""Thread-safe context vars for passing org/user identity into LLM calls."""
from contextvars import ContextVar
from typing import Optional, Tuple

_org_id: ContextVar[Optional[str]] = ContextVar("llm_org_id", default=None)
_user_id: ContextVar[Optional[str]] = ContextVar("llm_user_id", default=None)


def set_llm_context(org_id: Optional[str], user_id: Optional[str]) -> None:
    _org_id.set(org_id)
    _user_id.set(user_id)


def get_llm_context() -> Tuple[Optional[str], Optional[str]]:
    return _org_id.get(), _user_id.get()
