"""
Centralized Logging Configuration for QuantCoder
=================================================

Provides configurable logging with:
- Log rotation (size-based and time-based)
- Structured JSON logging option
- Per-module log level control
- Webhook alerting for failures
"""

import logging
import json
import os
from datetime import datetime
from logging.handlers import RotatingFileHandler, TimedRotatingFileHandler
from pathlib import Path
from typing import Optional, Dict, Any, Callable, List
from dataclasses import dataclass, field
import threading


@dataclass
class LoggingConfig:
    """Configuration for logging system."""
    level: str = "INFO"
    format: str = "standard"  # standard, json
    log_dir: Optional[Path] = None

    # File rotation settings
    max_file_size_mb: int = 10
    backup_count: int = 5
    rotate_when: str = "midnight"  # midnight, h (hourly), d (daily)

    # Per-module levels (module_name -> level)
    module_levels: Dict[str, str] = field(default_factory=dict)

    # Alerting
    alert_on_error: bool = False
    webhook_url: Optional[str] = None
    alert_levels: List[str] = field(default_factory=lambda: ["ERROR", "CRITICAL"])


class JSONFormatter(logging.Formatter):
    """JSON formatter for structured logging."""

    def format(self, record: logging.LogRecord) -> str:
        log_data = {
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "module": record.module,
            "function": record.funcName,
            "line": record.lineno,
        }

        # Add exception info if present
        if record.exc_info:
            log_data["exception"] = self.formatException(record.exc_info)

        # Add extra fields if present
        if hasattr(record, "extra_data"):
            log_data["extra"] = record.extra_data

        return json.dumps(log_data)


class WebhookHandler(logging.Handler):
    """Handler that sends alerts to a webhook URL."""

    def __init__(self, webhook_url: str, alert_levels: List[str] = None):
        super().__init__()
        self.webhook_url = webhook_url
        self.alert_levels = alert_levels or ["ERROR", "CRITICAL"]
        self._lock = threading.Lock()

    def emit(self, record: logging.LogRecord):
        if record.levelname not in self.alert_levels:
            return

        try:
            import requests

            payload = {
                "timestamp": datetime.utcnow().isoformat() + "Z",
                "level": record.levelname,
                "logger": record.name,
                "message": record.getMessage(),
                "module": record.module,
                "function": record.funcName,
            }

            if record.exc_info:
                payload["exception"] = self.format(record)

            with self._lock:
                requests.post(
                    self.webhook_url,
                    json=payload,
                    timeout=5,
                    headers={"Content-Type": "application/json"}
                )
        except Exception:
            # Don't let webhook failures break logging
            pass


class QuantCoderLogger:
    """
    Central logging manager for QuantCoder.

    Usage:
        from quantcoder.logging_config import setup_logging, get_logger

        # Setup once at startup
        setup_logging(verbose=True)

        # Get logger in any module
        logger = get_logger(__name__)
        logger.info("Starting process")
    """

    _instance = None
    _initialized = False

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self):
        if QuantCoderLogger._initialized:
            return
        self.config: Optional[LoggingConfig] = None
        self.handlers: List[logging.Handler] = []
        QuantCoderLogger._initialized = True

    def setup(
        self,
        verbose: bool = False,
        config: Optional[LoggingConfig] = None,
        console_handler: Optional[logging.Handler] = None,
    ):
        """
        Initialize logging system.

        Args:
            verbose: Enable DEBUG level logging
            config: Optional LoggingConfig for advanced settings
            console_handler: Optional custom console handler (e.g., RichHandler)
        """
        # Clean up existing handlers
        self.cleanup()

        # Use provided config or defaults
        self.config = config or LoggingConfig()

        # Determine log level
        if verbose:
            level = logging.DEBUG
        else:
            level = getattr(logging, self.config.level.upper(), logging.INFO)

        # Get log directory
        log_dir = self.config.log_dir or Path.home() / ".quantcoder" / "logs"
        log_dir.mkdir(parents=True, exist_ok=True)

        # Create root logger
        root_logger = logging.getLogger("quantcoder")
        root_logger.setLevel(level)

        # Choose formatter
        if self.config.format == "json":
            formatter = JSONFormatter()
        else:
            formatter = logging.Formatter(
                "%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
                datefmt="%Y-%m-%d %H:%M:%S"
            )

        # Console handler
        if console_handler:
            console_handler.setLevel(level)
            if not hasattr(console_handler, '_custom_formatter'):
                console_handler.setFormatter(formatter)
            root_logger.addHandler(console_handler)
            self.handlers.append(console_handler)
        else:
            console = logging.StreamHandler()
            console.setLevel(level)
            console.setFormatter(formatter)
            root_logger.addHandler(console)
            self.handlers.append(console)

        # Rotating file handler (size-based)
        log_file = log_dir / "quantcoder.log"
        file_handler = RotatingFileHandler(
            log_file,
            maxBytes=self.config.max_file_size_mb * 1024 * 1024,
            backupCount=self.config.backup_count,
        )
        file_handler.setLevel(level)
        file_handler.setFormatter(formatter)
        root_logger.addHandler(file_handler)
        self.handlers.append(file_handler)

        # JSON log file (always structured for parsing)
        json_log_file = log_dir / "quantcoder.json.log"
        json_handler = RotatingFileHandler(
            json_log_file,
            maxBytes=self.config.max_file_size_mb * 1024 * 1024,
            backupCount=self.config.backup_count,
        )
        json_handler.setLevel(level)
        json_handler.setFormatter(JSONFormatter())
        root_logger.addHandler(json_handler)
        self.handlers.append(json_handler)

        # Webhook handler for alerts
        if self.config.alert_on_error and self.config.webhook_url:
            webhook_handler = WebhookHandler(
                self.config.webhook_url,
                self.config.alert_levels
            )
            webhook_handler.setLevel(logging.ERROR)
            root_logger.addHandler(webhook_handler)
            self.handlers.append(webhook_handler)

        # Apply per-module log levels
        for module_name, module_level in self.config.module_levels.items():
            module_logger = logging.getLogger(module_name)
            module_logger.setLevel(getattr(logging, module_level.upper(), logging.INFO))

        # Reduce noise from third-party libraries
        logging.getLogger("urllib3").setLevel(logging.WARNING)
        logging.getLogger("requests").setLevel(logging.WARNING)
        logging.getLogger("httpx").setLevel(logging.WARNING)
        logging.getLogger("apscheduler").setLevel(logging.WARNING)

        root_logger.info(f"Logging initialized: level={logging.getLevelName(level)}, dir={log_dir}")

    def cleanup(self):
        """Remove all handlers from root logger."""
        root_logger = logging.getLogger("quantcoder")
        for handler in self.handlers:
            try:
                handler.close()
                root_logger.removeHandler(handler)
            except Exception:
                pass
        self.handlers.clear()

    def get_log_files(self) -> List[Path]:
        """Get list of all log files."""
        if not self.config or not self.config.log_dir:
            log_dir = Path.home() / ".quantcoder" / "logs"
        else:
            log_dir = self.config.log_dir

        if not log_dir.exists():
            return []

        return sorted(log_dir.glob("quantcoder*.log*"))


# Module-level functions for convenience
_logger_manager = QuantCoderLogger()


def setup_logging(
    verbose: bool = False,
    config: Optional[LoggingConfig] = None,
    console_handler: Optional[logging.Handler] = None,
):
    """
    Setup logging for QuantCoder.

    Call this once at application startup.

    Args:
        verbose: Enable DEBUG level
        config: Optional LoggingConfig for advanced settings
        console_handler: Optional custom console handler
    """
    _logger_manager.setup(verbose, config, console_handler)


def get_logger(name: str) -> logging.Logger:
    """
    Get a logger for a module.

    Args:
        name: Module name (typically __name__)

    Returns:
        Logger instance
    """
    # Ensure it's under quantcoder namespace
    if not name.startswith("quantcoder"):
        name = f"quantcoder.{name}"
    return logging.getLogger(name)


def get_log_files() -> List[Path]:
    """Get list of all log files."""
    return _logger_manager.get_log_files()


def log_with_context(
    logger: logging.Logger,
    level: int,
    message: str,
    **context
):
    """
    Log a message with additional context data.

    The context will appear in structured (JSON) logs.

    Args:
        logger: Logger instance
        level: Log level (logging.INFO, etc.)
        message: Log message
        **context: Additional context key-value pairs
    """
    record = logger.makeRecord(
        logger.name,
        level,
        "",
        0,
        message,
        (),
        None,
    )
    record.extra_data = context
    logger.handle(record)
