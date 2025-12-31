"""
Error Handling and Sanitization for Execution Service
Claire de Binare Trading Bot

Provides utilities to sanitize error messages and prevent information disclosure
to address penetration test finding L-01: The /orders endpoint returns raw
exception messages exposing internal details.

Usage:
    from error_handling import sanitize_error, SafeErrorResponse

    try:
        result = db.get_recent_orders()
    except Exception as e:
        logger.error("Database error: %s", e)  # Full error logged
        response = sanitize_error(e, request_id="abc123")
        return response.to_dict(), response.http_status
"""

import logging
from dataclasses import dataclass, field
from typing import Optional, Type

# Import deterministic UUID generator (follows project guardrails)
try:
    from core.utils.uuid_gen import generate_uuid_hex
except ImportError:
    from core.utils.uuid_gen import generate_uuid_hex

# Import validation error for type checking
try:
    from .validation import OrderValidationError
except ImportError:
    from validation import OrderValidationError


logger = logging.getLogger(__name__)


# =============================================================================
# Error Response Constants
# =============================================================================

# Standard safe error messages that don't expose internal details
ERROR_DATABASE_UNAVAILABLE = "Database temporarily unavailable"
ERROR_VALIDATION_FAILED = "Invalid request data"
ERROR_INTERNAL = "An internal error occurred"
ERROR_SERVICE_UNAVAILABLE = "Service temporarily unavailable"
ERROR_AUTHENTICATION_FAILED = "Authentication failed"
ERROR_RATE_LIMITED = "Too many requests"
ERROR_NOT_FOUND = "Resource not found"
ERROR_TIMEOUT = "Request timed out"


# HTTP Status codes for error types
HTTP_STATUS_BAD_REQUEST = 400
HTTP_STATUS_UNAUTHORIZED = 401
HTTP_STATUS_NOT_FOUND = 404
HTTP_STATUS_RATE_LIMITED = 429
HTTP_STATUS_INTERNAL_ERROR = 500
HTTP_STATUS_SERVICE_UNAVAILABLE = 503
HTTP_STATUS_GATEWAY_TIMEOUT = 504


# =============================================================================
# Error Code Constants
# =============================================================================

ERROR_CODE_DATABASE = "DATABASE_ERROR"
ERROR_CODE_VALIDATION = "VALIDATION_ERROR"
ERROR_CODE_INTERNAL = "INTERNAL_ERROR"
ERROR_CODE_SERVICE_UNAVAILABLE = "SERVICE_UNAVAILABLE"
ERROR_CODE_AUTHENTICATION = "AUTHENTICATION_ERROR"
ERROR_CODE_RATE_LIMITED = "RATE_LIMITED"
ERROR_CODE_NOT_FOUND = "NOT_FOUND"
ERROR_CODE_TIMEOUT = "TIMEOUT_ERROR"


# =============================================================================
# SafeErrorResponse Class
# =============================================================================

@dataclass
class SafeErrorResponse:
    """
    A safe, sanitized error response that doesn't expose internal details.

    This class provides a consistent structure for error responses that:
    - Uses generic, safe error messages
    - Includes a request ID for debugging/support
    - Maps to appropriate HTTP status codes
    - Never exposes stack traces or internal implementation details

    Attributes:
        code: A machine-readable error code (e.g., 'VALIDATION_ERROR')
        message: A human-readable safe error message
        request_id: Unique identifier for this request (for debugging)
        http_status: Appropriate HTTP status code for this error
        details: Optional list of safe error details (e.g., validation errors)
    """

    code: str
    message: str
    request_id: str = field(default_factory=lambda: generate_uuid_hex(length=8))
    http_status: int = HTTP_STATUS_INTERNAL_ERROR
    details: Optional[list[str]] = None

    def to_dict(self) -> dict:
        """
        Convert to a dictionary suitable for JSON API response.

        Returns:
            Dictionary with error, code, and request_id fields.
            Details are included only if present.
        """
        result = {
            "error": self.message,
            "code": self.code,
            "request_id": self.request_id,
        }
        if self.details:
            result["details"] = self.details
        return result

    def __str__(self) -> str:
        """String representation for logging."""
        return f"SafeErrorResponse({self.code}: {self.message}, request_id={self.request_id})"


# =============================================================================
# Exception to Safe Error Mapping
# =============================================================================

# Map exception types to (safe_message, error_code, http_status)
# Order matters - more specific exceptions should come first
_EXCEPTION_MAPPINGS: list[tuple[Type[Exception], str, str, int]] = []


def _init_exception_mappings() -> None:
    """
    Initialize exception mappings with common exception types.

    This function is called at module load time to populate the mappings.
    We use a function to avoid issues with import order.
    """
    global _EXCEPTION_MAPPINGS

    # Database-related exceptions (check these first)
    try:
        import psycopg2

        _EXCEPTION_MAPPINGS.extend([
            (psycopg2.OperationalError, ERROR_DATABASE_UNAVAILABLE, ERROR_CODE_DATABASE, HTTP_STATUS_SERVICE_UNAVAILABLE),
            (psycopg2.InterfaceError, ERROR_DATABASE_UNAVAILABLE, ERROR_CODE_DATABASE, HTTP_STATUS_SERVICE_UNAVAILABLE),
            (psycopg2.DatabaseError, ERROR_DATABASE_UNAVAILABLE, ERROR_CODE_DATABASE, HTTP_STATUS_SERVICE_UNAVAILABLE),
        ])
    except ImportError:
        pass

    # Redis-related exceptions
    try:
        import redis

        _EXCEPTION_MAPPINGS.extend([
            (redis.ConnectionError, ERROR_SERVICE_UNAVAILABLE, ERROR_CODE_SERVICE_UNAVAILABLE, HTTP_STATUS_SERVICE_UNAVAILABLE),
            (redis.TimeoutError, ERROR_TIMEOUT, ERROR_CODE_TIMEOUT, HTTP_STATUS_GATEWAY_TIMEOUT),
            (redis.RedisError, ERROR_SERVICE_UNAVAILABLE, ERROR_CODE_SERVICE_UNAVAILABLE, HTTP_STATUS_SERVICE_UNAVAILABLE),
        ])
    except ImportError:
        pass

    # Pydantic validation errors
    try:
        from pydantic import ValidationError

        _EXCEPTION_MAPPINGS.append(
            (ValidationError, ERROR_VALIDATION_FAILED, ERROR_CODE_VALIDATION, HTTP_STATUS_BAD_REQUEST)
        )
    except ImportError:
        pass

    # Standard Python exceptions (less specific, check last)
    _EXCEPTION_MAPPINGS.extend([
        (OrderValidationError, ERROR_VALIDATION_FAILED, ERROR_CODE_VALIDATION, HTTP_STATUS_BAD_REQUEST),
        (ValueError, ERROR_VALIDATION_FAILED, ERROR_CODE_VALIDATION, HTTP_STATUS_BAD_REQUEST),
        (TypeError, ERROR_VALIDATION_FAILED, ERROR_CODE_VALIDATION, HTTP_STATUS_BAD_REQUEST),
        (KeyError, ERROR_VALIDATION_FAILED, ERROR_CODE_VALIDATION, HTTP_STATUS_BAD_REQUEST),
        (TimeoutError, ERROR_TIMEOUT, ERROR_CODE_TIMEOUT, HTTP_STATUS_GATEWAY_TIMEOUT),
        (ConnectionError, ERROR_SERVICE_UNAVAILABLE, ERROR_CODE_SERVICE_UNAVAILABLE, HTTP_STATUS_SERVICE_UNAVAILABLE),
        (PermissionError, ERROR_AUTHENTICATION_FAILED, ERROR_CODE_AUTHENTICATION, HTTP_STATUS_UNAUTHORIZED),
        (FileNotFoundError, ERROR_NOT_FOUND, ERROR_CODE_NOT_FOUND, HTTP_STATUS_NOT_FOUND),
        (OSError, ERROR_INTERNAL, ERROR_CODE_INTERNAL, HTTP_STATUS_INTERNAL_ERROR),
    ])


# Initialize mappings at module load
_init_exception_mappings()


# =============================================================================
# Main Sanitization Function
# =============================================================================

def sanitize_error(
    exception: Exception,
    request_id: Optional[str] = None,
    log_full_error: bool = True,
) -> SafeErrorResponse:
    """
    Map an exception to a safe, generic error message.

    This function takes any exception and returns a SafeErrorResponse that:
    - Does not expose internal implementation details
    - Maps to an appropriate HTTP status code
    - Includes a request ID for support/debugging
    - Optionally logs the full error for debugging

    Args:
        exception: The exception to sanitize
        request_id: Optional request ID for tracking (generated if not provided)
        log_full_error: Whether to log the full exception (default: True)

    Returns:
        SafeErrorResponse with safe message and appropriate status code

    Example:
        >>> try:
        ...     raise ValueError("Internal secret: password=123")
        ... except Exception as e:
        ...     response = sanitize_error(e)
        ...     print(response.message)
        'Invalid request data'
    """
    # Generate request ID if not provided
    if request_id is None:
        request_id = generate_uuid_hex(length=8)

    # Log the full error for debugging (important for troubleshooting)
    if log_full_error:
        logger.error(
            "Error [request_id=%s]: %s: %s",
            request_id,
            type(exception).__name__,
            str(exception),
            exc_info=True,
        )

    # Special handling for OrderValidationError (has safe details)
    if isinstance(exception, OrderValidationError):
        return SafeErrorResponse(
            code=ERROR_CODE_VALIDATION,
            message=exception.message,
            request_id=request_id,
            http_status=HTTP_STATUS_BAD_REQUEST,
            details=exception.details if exception.details else None,
        )

    # Look up exception in our mappings
    for exc_type, safe_message, error_code, http_status in _EXCEPTION_MAPPINGS:
        if isinstance(exception, exc_type):
            return SafeErrorResponse(
                code=error_code,
                message=safe_message,
                request_id=request_id,
                http_status=http_status,
            )

    # Default: unknown exception type - use generic message
    return SafeErrorResponse(
        code=ERROR_CODE_INTERNAL,
        message=ERROR_INTERNAL,
        request_id=request_id,
        http_status=HTTP_STATUS_INTERNAL_ERROR,
    )


def sanitize_database_error(
    exception: Exception,
    request_id: Optional[str] = None,
) -> SafeErrorResponse:
    """
    Convenience function specifically for database errors.

    Always returns a database-related safe error regardless of exception type.
    Use this when you know the context is database-related.

    Args:
        exception: The exception that occurred
        request_id: Optional request ID for tracking

    Returns:
        SafeErrorResponse with database unavailable message
    """
    if request_id is None:
        request_id = generate_uuid_hex(length=8)

    logger.error(
        "Database error [request_id=%s]: %s: %s",
        request_id,
        type(exception).__name__,
        str(exception),
        exc_info=True,
    )

    return SafeErrorResponse(
        code=ERROR_CODE_DATABASE,
        message=ERROR_DATABASE_UNAVAILABLE,
        request_id=request_id,
        http_status=HTTP_STATUS_SERVICE_UNAVAILABLE,
    )


def sanitize_validation_error(
    exception: Exception,
    request_id: Optional[str] = None,
    details: Optional[list[str]] = None,
) -> SafeErrorResponse:
    """
    Convenience function specifically for validation errors.

    Args:
        exception: The exception that occurred
        request_id: Optional request ID for tracking
        details: Optional list of safe validation error details

    Returns:
        SafeErrorResponse with validation failed message
    """
    if request_id is None:
        request_id = generate_uuid_hex(length=8)

    logger.warning(
        "Validation error [request_id=%s]: %s: %s",
        request_id,
        type(exception).__name__,
        str(exception),
    )

    return SafeErrorResponse(
        code=ERROR_CODE_VALIDATION,
        message=ERROR_VALIDATION_FAILED,
        request_id=request_id,
        http_status=HTTP_STATUS_BAD_REQUEST,
        details=details,
    )


# =============================================================================
# Module Exports
# =============================================================================

__all__ = [
    # Main class and function
    "SafeErrorResponse",
    "sanitize_error",
    "sanitize_database_error",
    "sanitize_validation_error",
    # Error message constants
    "ERROR_DATABASE_UNAVAILABLE",
    "ERROR_VALIDATION_FAILED",
    "ERROR_INTERNAL",
    "ERROR_SERVICE_UNAVAILABLE",
    "ERROR_AUTHENTICATION_FAILED",
    "ERROR_RATE_LIMITED",
    "ERROR_NOT_FOUND",
    "ERROR_TIMEOUT",
    # Error code constants
    "ERROR_CODE_DATABASE",
    "ERROR_CODE_VALIDATION",
    "ERROR_CODE_INTERNAL",
    "ERROR_CODE_SERVICE_UNAVAILABLE",
    "ERROR_CODE_AUTHENTICATION",
    "ERROR_CODE_RATE_LIMITED",
    "ERROR_CODE_NOT_FOUND",
    "ERROR_CODE_TIMEOUT",
    # HTTP status codes
    "HTTP_STATUS_BAD_REQUEST",
    "HTTP_STATUS_UNAUTHORIZED",
    "HTTP_STATUS_NOT_FOUND",
    "HTTP_STATUS_RATE_LIMITED",
    "HTTP_STATUS_INTERNAL_ERROR",
    "HTTP_STATUS_SERVICE_UNAVAILABLE",
    "HTTP_STATUS_GATEWAY_TIMEOUT",
]
