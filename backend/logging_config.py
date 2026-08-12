# backend/logging_config.py
import logging
import sys
from backend.config import settings


def configure_logging():
    """Configures structured, readable console logging for the ULTRON API."""
    log_level = getattr(logging, settings.log_level.upper(), logging.INFO)

    # Standard log format matching prompt specification
    # e.g., 2026-08-11 12:00:00 INFO ULTRON API started
    log_format = "%(asctime)s %(levelname)s %(name)s - %(message)s"
    date_format = "%Y-%m-%d %H:%M:%S"

    # Avoid duplicate handlers on re-initialization
    root_logger = logging.getLogger()
    if root_logger.hasHandlers():
        root_logger.handlers.clear()

    logging.basicConfig(
        level=log_level,
        format=log_format,
        datefmt=date_format,
        handlers=[
            logging.StreamHandler(sys.stdout)
        ]
    )

    # Quiet external library loggers to prevent flood
    logging.getLogger("uvicorn.access").setLevel(logging.WARNING)
    logging.getLogger("uvicorn.error").setLevel(logging.INFO)

    logger = logging.getLogger("ultron-api")
    logger.info("Structured logging initialized at %s level", settings.log_level.upper())
    return logger
