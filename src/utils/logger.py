"""Structured logging utility for CLI output and audit trail."""

from __future__ import annotations

import logging
import sys
from src.config import settings


class Formatter(logging.Formatter):
    """Custom formatter with clean formatting for CLI and audit logs."""

    def format(self, record: logging.LogRecord) -> str:
        if record.levelno == logging.INFO:
            return f"{record.getMessage()}"
        elif record.levelno == logging.WARNING:
            return f"[WARNING] {record.getMessage()}"
        elif record.levelno == logging.ERROR:
            return f"[ERROR] {record.getMessage()}"
        elif record.levelno == logging.DEBUG:
            return f"[DEBUG] [{record.name}] {record.getMessage()}"
        return super().format(record)


def get_logger(name: str = "FaceBlockchain") -> logging.Logger:
    """Create and return a configured logger instance."""
    logger = logging.getLogger(name)
    if not logger.handlers:
        handler = logging.StreamHandler(sys.stdout)
        handler.setFormatter(Formatter())
        logger.addHandler(handler)
        logger.setLevel(getattr(logging, settings.log_level, logging.INFO))
        logger.propagate = False
    return logger


logger = get_logger()
