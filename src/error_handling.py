"""
Enhanced error handling and exception management for Liquid Hive.
Provides consistent error handling across all modules.
"""

import traceback
import sys
from typing import Any, Dict, Optional, Type, Union
from functools import wraps
from enum import Enum

from .logging_config import get_logger


class ErrorSeverity(Enum):
    """Error severity levels."""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class LiquidHiveError(Exception):
    """Base exception class for Liquid Hive."""

    def __init__(
        self,
        message: str,
        severity: ErrorSeverity = ErrorSeverity.MEDIUM,
        error_code: Optional[str] = None,
        context: Optional[Dict[str, Any]] = None,
        original_exception: Optional[Exception] = None
    ):
        super().__init__(message)
        self.message = message
        self.severity = severity
        self.error_code = error_code
        self.context = context or {}
        self.original_exception = original_exception
        self.traceback = traceback.format_exc()

    def to_dict(self) -> Dict[str, Any]:
        """Convert error to dictionary for serialization."""
        return {
            "error_type": self.__class__.__name__,
            "message": self.message,
            "severity": self.severity.value,
            "error_code": self.error_code,
            "context": self.context,
            "traceback": self.traceback
        }


class ConfigurationError(LiquidHiveError):
    """Raised when there's a configuration error."""
    pass


class AuthenticationError(LiquidHiveError):
    """Raised when authentication fails."""
    pass


class ValidationError(LiquidHiveError):
    """Raised when input validation fails."""
    pass


class NetworkError(LiquidHiveError):
    """Raised when network operations fail."""
    pass


class DatabaseError(LiquidHiveError):
    """Raised when database operations fail."""
    pass


class ModelError(LiquidHiveError):
    """Raised when model operations fail."""
    pass


class ResourceError(LiquidHiveError):
    """Raised when resource operations fail."""
    pass


class ErrorHandler:
    """Centralized error handling and reporting."""

    def __init__(self):
        self.logger = get_logger(__name__)
        self.error_counts = {}
        self.error_history = []

    def handle_error(
        self,
        error: Exception,
        context: Optional[Dict[str, Any]] = None,
        severity: ErrorSeverity = ErrorSeverity.MEDIUM,
        reraise: bool = True
    ) -> Optional[LiquidHiveError]:
        """
        Handle an error with proper logging and reporting.

        Args:
            error: The exception to handle
            context: Additional context about the error
            severity: Severity level of the error
            reraise: Whether to reraise the error as LiquidHiveError

        Returns:
            LiquidHiveError instance if reraise is False
        """
        # Convert to LiquidHiveError if needed
        if not isinstance(error, LiquidHiveError):
            liquid_error = LiquidHiveError(
                message=str(error),
                severity=severity,
                context=context or {},
                original_exception=error
            )
        else:
            liquid_error = error
            if context:
                liquid_error.context.update(context)

        # Log the error
        self._log_error(liquid_error)

        # Track error statistics
        self._track_error(liquid_error)

        # Add to error history
        self._add_to_history(liquid_error)

        if reraise:
            raise liquid_error

        return liquid_error

    def _log_error(self, error: LiquidHiveError):
        """Log the error with appropriate level."""
        log_message = f"Error {error.error_code or 'UNKNOWN'}: {error.message}"

        if error.context:
            log_message += f" | Context: {error.context}"

        if error.severity == ErrorSeverity.CRITICAL:
            self.logger.critical(log_message)
        elif error.severity == ErrorSeverity.HIGH:
            self.logger.error(log_message)
        elif error.severity == ErrorSeverity.MEDIUM:
            self.logger.warning(log_message)
        else:
            self.logger.info(log_message)

        # Log traceback for high severity errors
        if error.severity in [ErrorSeverity.HIGH, ErrorSeverity.CRITICAL]:
            self.logger.debug(f"Traceback: {error.traceback}")

    def _track_error(self, error: LiquidHiveError):
        """Track error statistics."""
        error_key = f"{error.__class__.__name__}:{error.error_code or 'UNKNOWN'}"
        self.error_counts[error_key] = self.error_counts.get(error_key, 0) + 1

    def _add_to_history(self, error: LiquidHiveError):
        """Add error to history (keep last 100)."""
        self.error_history.append(error)
        if len(self.error_history) > 100:
            self.error_history.pop(0)

    def get_error_stats(self) -> Dict[str, Any]:
        """Get error statistics."""
        return {
            "total_errors": sum(self.error_counts.values()),
            "error_counts": self.error_counts,
            "recent_errors": len(self.error_history)
        }

    def get_recent_errors(self, limit: int = 10) -> list:
        """Get recent errors."""
        return self.error_history[-limit:]


# Global error handler instance
error_handler = ErrorHandler()


def handle_errors(
    severity: ErrorSeverity = ErrorSeverity.MEDIUM,
    reraise: bool = True,
    context: Optional[Dict[str, Any]] = None
):
    """
    Decorator to handle errors in functions.

    Args:
        severity: Default severity level for errors
        reraise: Whether to reraise errors
        context: Additional context to include with errors
    """
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            try:
                return func(*args, **kwargs)
            except Exception as e:
                return error_handler.handle_error(
                    e,
                    context=context,
                    severity=severity,
                    reraise=reraise
                )
        return wrapper
    return decorator


def safe_execute(
    func,
    *args,
    severity: ErrorSeverity = ErrorSeverity.MEDIUM,
    default_return: Any = None,
    context: Optional[Dict[str, Any]] = None,
    **kwargs
) -> Any:
    """
    Safely execute a function with error handling.

    Args:
        func: Function to execute
        *args: Function arguments
        severity: Error severity level
        default_return: Value to return if function fails
        context: Additional context for error
        **kwargs: Function keyword arguments

    Returns:
        Function result or default_return if error occurs
    """
    try:
        return func(*args, **kwargs)
    except Exception as e:
        error_handler.handle_error(
            e,
            context=context,
            severity=severity,
            reraise=False
        )
        return default_return


def validate_input(
    value: Any,
    validator: callable,
    error_message: str,
    severity: ErrorSeverity = ErrorSeverity.MEDIUM
) -> Any:
    """
    Validate input with custom validator.

    Args:
        value: Value to validate
        validator: Validation function
        error_message: Error message if validation fails
        severity: Error severity level

    Returns:
        Validated value

    Raises:
        ValidationError: If validation fails
    """
    try:
        if not validator(value):
            raise ValidationError(
                message=error_message,
                severity=severity,
                context={"value": str(value), "validator": validator.__name__}
            )
        return value
    except Exception as e:
        if isinstance(e, ValidationError):
            raise
        raise ValidationError(
            message=f"Validation error: {str(e)}",
            severity=severity,
            context={"value": str(value), "validator": validator.__name__},
            original_exception=e
        )


def retry_on_error(
    max_retries: int = 3,
    delay: float = 1.0,
    backoff_factor: float = 2.0,
    exceptions: tuple = (Exception,)
):
    """
    Decorator to retry function on error.

    Args:
        max_retries: Maximum number of retries
        delay: Initial delay between retries
        backoff_factor: Multiplier for delay after each retry
        exceptions: Tuple of exceptions to retry on
    """
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            last_exception = None
            current_delay = delay

            for attempt in range(max_retries + 1):
                try:
                    return func(*args, **kwargs)
                except exceptions as e:
                    last_exception = e
                    if attempt < max_retries:
                        error_handler.logger.warning(
                            f"Attempt {attempt + 1} failed: {str(e)}. "
                            f"Retrying in {current_delay}s..."
                        )
                        import time
                        time.sleep(current_delay)
                        current_delay *= backoff_factor
                    else:
                        error_handler.logger.error(
                            f"All {max_retries + 1} attempts failed. Last error: {str(e)}"
                        )

            # If we get here, all retries failed
            raise last_exception

        return wrapper
    return decorator


# Convenience functions
def log_and_continue(error: Exception, context: Optional[Dict[str, Any]] = None):
    """Log error and continue execution."""
    return error_handler.handle_error(
        error,
        context=context,
        severity=ErrorSeverity.LOW,
        reraise=False
    )


def log_and_reraise(error: Exception, context: Optional[Dict[str, Any]] = None):
    """Log error and reraise."""
    return error_handler.handle_error(
        error,
        context=context,
        severity=ErrorSeverity.HIGH,
        reraise=True
    )


def get_error_stats() -> Dict[str, Any]:
    """Get current error statistics."""
    return error_handler.get_error_stats()


def get_recent_errors(limit: int = 10) -> list:
    """Get recent errors."""
    return error_handler.get_recent_errors(limit)
