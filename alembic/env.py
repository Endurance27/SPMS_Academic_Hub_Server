import asyncio
import os
import sys
from logging.config import fileConfig
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]  # repo root (one level above /alembic)
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import json

# normalize list-style env vars so pydantic_settings won't try json.loads on CSV/empty values
for _k in ("ALLOWED_HOSTS", "CORS_ORIGINS", "ALLOWED_EXTENSIONS"):
    if _k in os.environ:
        val = os.environ.get(_k, "")
        if val is None or str(val).strip() == "":
            os.environ.pop(_k, None)
        else:
            s = str(val).strip()
            if not (s.startswith("[") or s.startswith("{")):
                items = [i.strip() for i in s.split(",") if i.strip()]
                os.environ[_k] = json.dumps(items)

from sqlalchemy import pool
from sqlalchemy.engine import Connection
from sqlalchemy.ext.asyncio import AsyncEngine, create_async_engine

import app.models
from alembic import context

# ensure project package is on PYTHONPATH in your env when running alembic
# Import your Base and models so metadata is populated
from app.core.database import Base  # noqa: E402

# this is the Alembic Config object, which provides access to the values
# in the .ini file in use.
config = context.config

# Interpret the config file for Python logging.
if config.config_file_name:
    fileConfig(config.config_file_name)

# Provide target metadata for 'autogenerate'
target_metadata = Base.metadata


def get_url():
    # Prefer DATABASE_URL environment variable (set in your .env / docker-compose)
    url = os.environ.get("DATABASE_URL")
    if url:
        return url
    # optional fallback (be careful: importing settings may trigger env parsing)
    try:
        from app.core.config import settings

        return settings.DATABASE_URL
    except Exception:
        return config.get_main_option("sqlalchemy.url")


def run_migrations_offline():
    url = get_url()
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )

    with context.begin_transaction():
        context.run_migrations()


def do_run_migrations(connection: Connection):
    context.configure(connection=connection, target_metadata=target_metadata)

    with context.begin_transaction():
        context.run_migrations()


async def run_migrations_online():
    connectable = create_async_engine(
        get_url(),
        poolclass=pool.NullPool,
    )

    async with connectable.connect() as connection:
        await connection.run_sync(do_run_migrations)
    await connectable.dispose()


if context.is_offline_mode():
    run_migrations_offline()
else:
    asyncio.run(run_migrations_online())
