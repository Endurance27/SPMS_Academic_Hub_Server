#!/usr/bin/env python3
"""
Database migration script for production deployments.
Runs Alembic migrations to upgrade the database schema.
"""
import asyncio
import sys
from loguru import logger


async def run_migrations():
    """Run Alembic migrations"""
    try:
        logger.info("Running database migrations...")

        # Import here to avoid issues with async
        from alembic.config import Config
        from alembic import command

        # Configure Alembic
        alembic_cfg = Config("alembic.ini")

        # Run upgrade
        command.upgrade(alembic_cfg, "head")

        logger.info("Database migrations completed successfully!")
        return True
    except Exception as e:
        logger.error(f"Migration failed: {e}")
        return False


if __name__ == "__main__":
    success = asyncio.run(run_migrations())
    sys.exit(0 if success else 1)
