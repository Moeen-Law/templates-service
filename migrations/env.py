from __future__ import annotations

import os
from logging.config import fileConfig

from alembic import context
from sqlalchemy import engine_from_config, pool

from app.core.config import Settings
from app.core.vault import load_vault_secrets_into_environment
from app.models.base import Base
from app.models.template import DocumentTemplate, TemplateField

config = context.config

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

bootstrap_settings = Settings()
load_vault_secrets_into_environment(
    enabled=bootstrap_settings.vault_enabled,
    vault_addr=bootstrap_settings.vault_addr,
    vault_token=bootstrap_settings.vault_token,
    kv_mount=bootstrap_settings.vault_kv_mount,
    kv_path=bootstrap_settings.vault_kv_path,
    timeout_seconds=bootstrap_settings.vault_timeout_seconds,
    namespace=bootstrap_settings.vault_namespace,
    fail_fast=bootstrap_settings.vault_fail_fast,
    skip_verify=bootstrap_settings.vault_skip_verify,
    ca_cert_path=bootstrap_settings.vault_cacert,
)
if "DATABASE_URL" not in os.environ and bootstrap_settings.database_url:
    os.environ["DATABASE_URL"] = bootstrap_settings.database_url


def _get_sync_database_url() -> str:
    url = os.getenv("DATABASE_URL") or config.get_main_option("sqlalchemy.url")
    if "+aiosqlite" in url:
        return url.replace("+aiosqlite", "")
    if "+asyncpg" in url:
        return url.replace("+asyncpg", "+psycopg")
    return url


config.set_main_option("sqlalchemy.url", _get_sync_database_url())

target_metadata = Base.metadata


def run_migrations_offline() -> None:
    url = config.get_main_option("sqlalchemy.url")
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
    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
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
