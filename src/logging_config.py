"""
Structured logging configuration.
Supports JSON format for structured log analysis.
"""

import logging
import logging.handlers
import os
import sys
from pathlib import Path
from typing import Optional

import structlog
from pythonjsonlogger import jsonlogger

from src.config import settings
from src.utils.context import get_correlation_id, get_user_id, get_session_id


def configure_logging(log_level: Optional[str] = None) -> None:
    """
    Configure structured logging for the application.

    Args:
        log_level: Override log level from settings
    """
    level = log_level or settings.log_level
    log_format = settings.log_format

    if log_format == "json":
        # JSON logging for ELK Stack
        configure_json_logging(level)
    else:
        # Standard logging for development
        configure_standard_logging(level)


def add_context_to_log(logger, method_name, event_dict):
    """
    Structlog processor to add context variables (correlation_id, user_id, etc.)
    to every log entry automatically.
    """
    correlation_id = get_correlation_id()
    if correlation_id:
        event_dict["correlation_id"] = correlation_id

    user_id = get_user_id()
    if user_id:
        event_dict["user_id"] = user_id

    session_id = get_session_id()
    if session_id:
        event_dict["session_id"] = session_id

    return event_dict


def configure_json_logging(level: str) -> None:
    """Configure JSON logging for production."""
    # Custom JSON formatter
    class CustomJsonFormatter(jsonlogger.JsonFormatter):
        def add_fields(self, log_record, record, message_dict):
            super().add_fields(log_record, record, message_dict)
            log_record["timestamp"] = record.created
            log_record["level"] = record.levelname
            log_record["logger"] = record.name
            log_record["service"] = settings.app_name

            # Add context variables from contextvars
            correlation_id = get_correlation_id()
            if correlation_id:
                log_record["correlation_id"] = correlation_id

            user_id = get_user_id()
            if user_id:
                log_record["user_id"] = user_id

            session_id = get_session_id()
            if session_id:
                log_record["session_id"] = session_id

    json_formatter = CustomJsonFormatter(
        "%(timestamp)s %(level)s %(name)s %(message)s"
    )

    # Console handler (stdout)
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(json_formatter)

    # File handler (for log aggregation)
    log_dir = Path(os.environ.get("LOG_DIR", "/app/logs"))
    handlers = [console_handler]
    if log_dir.exists() or os.environ.get("ENVIRONMENT", "").lower() == "production":
        log_dir.mkdir(parents=True, exist_ok=True)
        file_handler = logging.handlers.RotatingFileHandler(
            log_dir / "app.log",
            maxBytes=50 * 1024 * 1024,  # 50 MB
            backupCount=5,
            encoding="utf-8",
        )
        file_handler.setFormatter(json_formatter)
        handlers.append(file_handler)

    logging.root.handlers = handlers
    logging.root.setLevel(level)

    # Configure structlog with context processor
    structlog.configure(
        processors=[
            structlog.stdlib.filter_by_level,
            structlog.stdlib.add_logger_name,
            structlog.stdlib.add_log_level,
            structlog.processors.TimeStamper(fmt="iso"),
            add_context_to_log,  # Add context variables automatically
            structlog.processors.JSONRenderer(),
        ],
        context_class=dict,
        logger_factory=structlog.stdlib.LoggerFactory(),
        wrapper_class=structlog.stdlib.BoundLogger,
        cache_logger_on_first_use=True,
    )


def configure_standard_logging(level: str) -> None:
    """Configure standard logging for development."""
    logging.basicConfig(
        level=level,
        format="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
        handlers=[logging.StreamHandler(sys.stdout)],
    )

    # Configure structlog for pretty printing with context
    structlog.configure(
        processors=[
            structlog.stdlib.filter_by_level,
            structlog.stdlib.add_logger_name,
            structlog.stdlib.add_log_level,
            add_context_to_log,  # Add context variables in dev mode too
            structlog.dev.ConsoleRenderer(colors=True),
        ],
        context_class=dict,
        logger_factory=structlog.stdlib.LoggerFactory(),
        wrapper_class=structlog.stdlib.BoundLogger,
        cache_logger_on_first_use=True,
    )


def get_logger(name: str) -> structlog.BoundLogger:
    """
    Get a structured logger instance.

    Args:
        name: Logger name (usually __name__)

    Returns:
        Configured structlog logger
    """
    return structlog.get_logger(name)
