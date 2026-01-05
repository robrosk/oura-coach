"""Logging configuration."""

import logging
import sys

from .config import get_settings


def setup_logging() -> logging.Logger:
    """Configure and return the application logger."""
    settings = get_settings()

    # Configure root logger
    logging.basicConfig(
        level=settings.log_level,
        format="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
        handlers=[logging.StreamHandler(sys.stdout)],
    )

    logger = logging.getLogger("oura_agent")
    logger.setLevel(settings.log_level)

    return logger


# Module-level logger
logger = setup_logging()
