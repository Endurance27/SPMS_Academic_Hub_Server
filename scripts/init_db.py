import asyncio

from loguru import logger

from app.core.database import init_db


async def initialize_database():
    """Initialize database tables"""
    try:
        logger.info("Initializing database...")
        await init_db()
        logger.info("Database initialized successfully!")
    except Exception as e:
        logger.error(f"Error initializing database: {e}")
        raise


if __name__ == "__main__":
    asyncio.run(initialize_database())
