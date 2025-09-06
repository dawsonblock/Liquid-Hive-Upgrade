"""
Centralized logging configuration for Liquid Hive.
Provides consistent logging across all modules.
"""

import logging
import sys
from pathlib import Path
from typing import Optional
from datetime import datetime


class ColoredFormatter(logging.Formatter):
    """Custom formatter with colors for console output."""

    # Color codes
    COLORS = {
        'DEBUG': '\033[36m',     # Cyan
        'INFO': '\033[32m',      # Green
        'WARNING': '\033[33m',   # Yellow
        'ERROR': '\033[31m',     # Red
        'CRITICAL': '\033[35m',  # Magenta
        'RESET': '\033[0m'       # Reset
    }

    def format(self, record):
        # Add color to levelname
        if record.levelname in self.COLORS:
            record.levelname = f"{self.COLORS[record.levelname]}{record.levelname}{self.COLORS['RESET']}"

        return super().format(record)


def setup_logging(
    level: str = "INFO",
    log_file: Optional[str] = None,
    enable_console: bool = True,
    enable_colors: bool = True
) -> logging.Logger:
    """
    Set up centralized logging configuration.

    Args:
        level: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        log_file: Optional file path for log output
        enable_console: Whether to enable console output
        enable_colors: Whether to use colored console output

    Returns:
        Configured logger instance
    """
    # Create logger
    logger = logging.getLogger("liquid_hive")
    logger.setLevel(getattr(logging, level.upper()))

    # Clear existing handlers
    logger.handlers.clear()

    # Create formatters
    if enable_colors and enable_console:
        console_formatter = ColoredFormatter(
            '%(asctime)s | %(levelname)-8s | %(name)s | %(message)s',
            datefmt='%H:%M:%S'
        )
    else:
        console_formatter = logging.Formatter(
            '%(asctime)s | %(levelname)-8s | %(name)s | %(message)s',
            datefmt='%H:%M:%S'
        )

    file_formatter = logging.Formatter(
        '%(asctime)s | %(levelname)-8s | %(name)s | %(funcName)s:%(lineno)d | %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )

    # Console handler
    if enable_console:
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setFormatter(console_formatter)
        console_handler.setLevel(getattr(logging, level.upper()))
        logger.addHandler(console_handler)

    # File handler
    if log_file:
        # Ensure log directory exists
        log_path = Path(log_file)
        log_path.parent.mkdir(parents=True, exist_ok=True)

        file_handler = logging.FileHandler(log_file)
        file_handler.setFormatter(file_formatter)
        file_handler.setLevel(logging.DEBUG)  # File gets all levels
        logger.addHandler(file_handler)

    # Prevent duplicate logs
    logger.propagate = False

    return logger


def get_logger(name: str) -> logging.Logger:
    """
    Get a logger instance for a specific module.

    Args:
        name: Module name (usually __name__)

    Returns:
        Logger instance
    """
    return logging.getLogger(f"liquid_hive.{name}")


# Default setup
def init_logging():
    """Initialize logging with default configuration."""
    # Create logs directory
    logs_dir = Path("logs")
    logs_dir.mkdir(exist_ok=True)

    # Set up logging
    log_file = logs_dir / f"liquid_hive_{datetime.now().strftime('%Y%m%d')}.log"

    return setup_logging(
        level="INFO",
        log_file=str(log_file),
        enable_console=True,
        enable_colors=True
    )


# Convenience functions
def debug(message: str, *args, **kwargs):
    """Log debug message."""
    logger = get_logger("debug")
    logger.debug(message, *args, **kwargs)


def info(message: str, *args, **kwargs):
    """Log info message."""
    logger = get_logger("info")
    logger.info(message, *args, **kwargs)


def warning(message: str, *args, **kwargs):
    """Log warning message."""
    logger = get_logger("warning")
    logger.warning(message, *args, **kwargs)


def error(message: str, *args, **kwargs):
    """Log error message."""
    logger = get_logger("error")
    logger.error(message, *args, **kwargs)


def critical(message: str, *args, **kwargs):
    """Log critical message."""
    logger = get_logger("critical")
    logger.critical(message, *args, **kwargs)


# Initialize default logging
if not logging.getLogger("liquid_hive").handlers:
    init_logging()
