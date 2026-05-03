"""Logging setup utilities for le-tour."""

import logging
import logging.handlers
import json
import sys
from datetime import datetime
from typing import Optional

from .config import get_config


class JSONLFormatter(logging.Formatter):
    """Custom formatter for JSONL (JSON Lines) log format."""

    def format(self, record: logging.LogRecord) -> str:
        """Format log record as JSON line."""
        # Create base log entry
        log_entry = {
            "timestamp": datetime.fromtimestamp(record.created).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }

        # Add exception info if present
        if record.exc_info:
            log_entry["exception"] = self.formatException(record.exc_info)

        # Add extra fields from record
        if hasattr(record, "event_type"):
            log_entry["event_type"] = record.event_type

        if hasattr(record, "extra_data"):
            log_entry.update(record.extra_data)

        return json.dumps(log_entry, separators=(",", ":"))


def setup_logging(
    app_log_level: str = "INFO",
    lib_log_level: str = "WARNING",
    console_output: bool = True,
    max_file_size: int = 10 * 1024 * 1024,  # 10MB
    backup_count: int = 5,
) -> None:
    """Set up logging configuration for le-tour.

    Args:
        app_log_level: Log level for application code
        lib_log_level: Log level for library code
        console_output: Whether to output logs to console
        max_file_size: Maximum size of log files before rotation
        backup_count: Number of backup log files to keep
    """
    config = get_config()

    # Create formatters
    jsonl_formatter = JSONLFormatter()
    console_formatter = logging.Formatter(
        "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    )

    # Configure root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(logging.DEBUG)  # Capture all messages

    # Clear any existing handlers
    root_logger.handlers.clear()

    # File handler with rotation (JSONL format)
    file_handler = logging.handlers.RotatingFileHandler(
        config.get_log_file_path("le-tour"),
        maxBytes=max_file_size,
        backupCount=backup_count,
        encoding="utf-8",
    )
    file_handler.setLevel(getattr(logging, app_log_level.upper()))
    file_handler.setFormatter(jsonl_formatter)
    root_logger.addHandler(file_handler)

    # Console handler (if enabled)
    if console_output:
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(getattr(logging, app_log_level.upper()))
        console_handler.setFormatter(console_formatter)
        root_logger.addHandler(console_handler)

    # Set library log levels
    lib_level = getattr(logging, lib_log_level.upper())

    # Suppress noisy library loggers
    logging.getLogger("bleak").setLevel(lib_level)
    logging.getLogger("asyncio").setLevel(lib_level)
    logging.getLogger("rich").setLevel(lib_level)

    # Application loggers at app level
    logging.getLogger("le-tour").setLevel(getattr(logging, app_log_level.upper()))


def log_event(event_type: str, **kwargs) -> None:
    """Log a structured event in JSONL format.

    Args:
        event_type: Type of event (e.g., 'session_started', 'device_connected')
        **kwargs: Additional event data
    """
    logger = logging.getLogger("le-tour.events")

    # Create log record with extra data
    extra_data = {"event_type": event_type, "extra_data": kwargs}
    logger.info(f"{event_type}", extra=extra_data)


# Convenience functions for common events
def log_session_started(session_id: str, mode: str, **kwargs) -> None:
    """Log session start event."""
    log_event("session_started", session_id=session_id, mode=mode, **kwargs)


def log_session_ended(session_id: str, duration_s: float, **kwargs) -> None:
    """Log session end event."""
    log_event("session_ended", session_id=session_id, duration_s=duration_s, **kwargs)


def log_device_connected(device_type: str, device_name: str, **kwargs) -> None:
    """Log device connection event."""
    log_event(
        "device_connected", device_type=device_type, device_name=device_name, **kwargs
    )


def log_device_disconnected(device_type: str, device_name: str, **kwargs) -> None:
    """Log device disconnection event."""
    log_event(
        "device_disconnected",
        device_type=device_type,
        device_name=device_name,
        **kwargs,
    )


def log_sample(
    power_w: Optional[int],
    cadence_rpm: Optional[int],
    speed_mps: Optional[float],
    **kwargs,
) -> None:
    """Log training data sample."""
    log_event(
        "sample",
        power_w=power_w,
        cadence_rpm=cadence_rpm,
        speed_mps=speed_mps,
        **kwargs,
    )


def log_error(error_code: str, message: str, **kwargs) -> None:
    """Log error event."""
    logger = logging.getLogger("le-tour.errors")
    extra_data = {"event_type": "error", "extra_data": {"code": error_code, **kwargs}}
    logger.error(message, extra=extra_data)
