import os
import sys
from logging.config import fileConfig
from pathlib import Path

from alembic import context
from sqlalchemy import engine_from_config, pool

# Ensure project root is on path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from services.db.base import Base
from services.db.session import get_database_url

# Import all models so metadata is populated
import models.organization  # noqa
import models.policy  # noqa
import models.control  # noqa
import models.evidence  # noqa
import models.gap  # noqa
import models.task  # noqa
import models.readiness  # noqa
import models.audit_log  # noqa
import models.app_settings  # noqa
import models.control_registry  # noqa
import models.eval_store  # noqa
import models.feedback  # noqa
import models.policy_version  # noqa

config = context.config
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = Base.metadata


def get_url():
    return os.getenv("DATABASE_URL") or get_database_url()


def run_migrations_offline() -> None:
    url = get_url()
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        compare_type=True,
    )
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    configuration = config.get_section(config.config_ini_section, {})
    configuration["sqlalchemy.url"] = get_url()
    connectable = engine_from_config(
        configuration,
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )
    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            compare_type=True,
        )
        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
