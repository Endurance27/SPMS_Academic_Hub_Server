import logging
import sys

from loguru import logger
from pythonjsonlogger import jsonlogger

from app.core.config import settings


class InterceptHandler(logging.Handler):
    """Intercept standard logging and route to loguru"""

    def emit(self, record: logging.LogRecord) -> None:
        try:
            level = logger.level(record.levelname).name
        except ValueError:
            level = record.levelno

        frame, depth = logging.currentframe(), 2
        while frame.f_code.co_filename == logging.__file__:
            frame = frame.f_back
            depth += 1

        logger.opt(depth=depth, exception=record.exc_info).log(level, record.getMessage())


def setup_logging() -> None:
    """Setup logging configuration"""
    # Remove default handlers
    logger.remove()

    # Add console handler
    logger.add(
        sys.stdout,
        level=settings.LOG_LEVEL,
        format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{function}</cyan> - <level>{message}</level>",
        colorize=True,
    )

    # Add file handler
    logger.add(
        "logs/app.log",
        rotation="500 MB",
        retention="10 days",
        level=settings.LOG_LEVEL,
        format="{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | {name}:{function} - {message}",
    )

    # Add JSON handler for Logstash
    if settings.APP_ENV == "production":
        logger.add(
            f"logs/app.json",
            serialize=True,
            rotation="500 MB",
            retention="10 days",
            level=settings.LOG_LEVEL,
        )

    # Intercept standard logging
    logging.basicConfig(handlers=[InterceptHandler()], level=0)

    # Set levels for third-party loggers
    for logger_name in ["uvicorn", "uvicorn.access", "fastapi"]:
        logging_logger = logging.getLogger(logger_name)
        logging_logger.handlers = [InterceptHandler()]
