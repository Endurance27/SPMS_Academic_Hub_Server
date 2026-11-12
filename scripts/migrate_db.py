#!/usr/bin/env python3
"""
Database migration script for production deployments.
Runs Alembic migrations to upgrade the database schema.
"""
import sys
from loguru import logger


def run_migrations():
    """Run Alembic migrations."""
    try:
        logger.info("Running database migrations...")

        from alembic.config import Config
        from alembic import command

        alembic_cfg = Config("alembic.ini")
        command.upgrade(alembic_cfg, "head")

        logger.info("Database migrations completed successfully!")
        return True
    except Exception as e:
        logger.error(f"Migration failed: {e}")
        return False


if __name__ == "__main__":
    success = run_migrations()
    sys.exit(0 if success else 1)
