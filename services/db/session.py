"""Database engine and session helpers for local development and future migrations.

The default setup uses SQLite so the app can start adopting database-backed
storage incrementally. Setting ``DATABASE_URL`` lets the same models work with
PostgreSQL later without changing application code.
"""

from __future__ import annotations

import os
from contextlib import contextmanager
from pathlib import Path
from typing import Generator

from sqlalchemy import Engine, create_engine
from sqlalchemy.orm import Session, sessionmaker

from services.db.base import Base


def get_database_url() -> str:
    """Return the configured database URL, defaulting to a local SQLite file."""

    configured = os.getenv("DATABASE_URL")
    if configured:
        return configured

    default_path = (Path("data") / "app.db").resolve()
    default_path.parent.mkdir(parents=True, exist_ok=True)
    return f"sqlite:///{default_path}"


def get_engine(database_url: str | None = None) -> Engine:
    """Build a SQLAlchemy engine with sensible defaults for the current backend."""

    url = database_url or get_database_url()
    connect_args = {"check_same_thread": False} if url.startswith("sqlite") else {}
    echo = os.getenv("SQLALCHEMY_ECHO", "").lower() in {"1", "true", "yes", "on"}
    return create_engine(url, future=True, echo=echo, connect_args=connect_args)


ENGINE = get_engine()
SessionLocal = sessionmaker(bind=ENGINE, autoflush=False, autocommit=False, expire_on_commit=False, class_=Session)


def _import_models() -> None:
    """Import ORM model modules so metadata is fully registered before create_all."""

    import models.control  # noqa: F401
    import models.evidence  # noqa: F401
    import models.gap  # noqa: F401
    import models.organization  # noqa: F401
    import models.policy  # noqa: F401
    import models.readiness  # noqa: F401
    import models.task  # noqa: F401


def create_all_tables(engine: Engine | None = None) -> None:
    """Create all known tables for local development or first-run setup."""

    _import_models()
    Base.metadata.create_all(bind=engine or ENGINE)


def get_session() -> Session:
    """Return a new ORM session for short-lived use."""

    return SessionLocal()


@contextmanager
def session_scope() -> Generator[Session, None, None]:
    """Provide a transactional session scope with automatic commit/rollback."""

    session = get_session()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()
